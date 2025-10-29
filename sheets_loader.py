# sheets_loader.py para AlphaBot
# Baseado no Quasar Analytics
import os
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Funções utilitárias para ler configs do st.secrets ou env
import streamlit as st

def get_google_service_account_credentials():
    info = st.secrets.get("google_service_account")
    if info:
        return service_account.Credentials.from_service_account_info(info, scopes=[
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/spreadsheets.readonly',
        ])
    raise RuntimeError("Credenciais da Service Account não encontradas em st.secrets['google_service_account']")

def get_sheets_folder_id() -> str:
    return st.secrets.get("SHEETS_FOLDER_ID", "") or os.getenv("SHEETS_FOLDER_ID", "")

def get_sheets_ids() -> List[str]:
    ids = st.secrets.get("SHEETS_IDS", "") or os.getenv("SHEETS_IDS", "")
    return [i.strip() for i in ids.split(",") if i.strip()]

def get_sheet_range(default: str = "A:Z") -> str:
    return st.secrets.get("SHEET_RANGE", default) or os.getenv("SHEET_RANGE", default)

class SheetsLoader:
    def __init__(self, sheet_ids: Optional[List[str]] = None, sheet_range: str = "A:Z"):
        self.sheet_ids = sheet_ids or get_sheets_ids()
        self.sheet_folder_id = get_sheets_folder_id() or ""
        self.sheet_range = get_sheet_range(sheet_range)
        self._sheets = None
        self._drive = None
        self._cache: Dict[str, pd.DataFrame] = {}
        self._last_errors: List[str] = []

    def _auth(self):
        creds = get_google_service_account_credentials()
        self._drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        self._sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)

    def _ensure_clients(self):
        if self._sheets is None or self._drive is None:
            self._auth()

    def _resolve_sheet_ids(self) -> List[str]:
        ids: List[str] = []
        if self.sheet_folder_id:
            try:
                self._ensure_clients()
                page_token = None
                while True:
                    results = self._drive.files().list(
                        q=f"mimeType='application/vnd.google-apps.spreadsheet' and '{self.sheet_folder_id}' in parents and trashed=false",
                        pageSize=100,
                        fields="nextPageToken, files(id, name)",
                        pageToken=page_token
                    ).execute()
                    files = results.get('files', [])
                    ids.extend([f['id'] for f in files])
                    page_token = results.get('nextPageToken')
                    if not page_token:
                        break
            except Exception as e:
                self._last_errors.append(f"Drive listing error: {e}")
        for x in self.sheet_ids:
            if x and x not in ids:
                ids.append(x)
        ids = [i for i in ids if i]
        return list(dict.fromkeys(ids))

    def load_all(self) -> Tuple[int, int]:
        self._ensure_clients()
        prev_cache = self._cache
        new_cache: Dict[str, pd.DataFrame] = {}
        total_rows = 0
        loaded = 0
        try:
            sheet_ids_to_load = self._resolve_sheet_ids()
            for sheet_id in sheet_ids_to_load:
                meta = self._sheets.spreadsheets().get(spreadsheetId=sheet_id).execute()
                for sheet in meta.get('sheets', []):
                    ws_title = sheet['properties']['title']
                    range_full = f"'{ws_title}'!{self.sheet_range}"
                    result = self._sheets.spreadsheets().values().get(
                        spreadsheetId=sheet_id,
                        range=range_full
                    ).execute()
                    values = result.get('values', [])
                    if not values:
                        continue
                    headers = values[0]
                    data_rows = values[1:]
                    df = pd.DataFrame(data_rows, columns=headers)
                    key = f"{sheet_id}::{ws_title}"
                    new_cache[key] = df
                    total_rows += len(df)
                    loaded += 1
            self._cache = new_cache
            return loaded, total_rows
        except Exception as e:
            self._cache = prev_cache
            self._last_errors.append(f"Unexpected load error: {e}")
            raise

    def is_configured(self) -> bool:
        try:
            _ = get_google_service_account_credentials()
            return bool(self.sheet_folder_id) or bool(self.sheet_ids)
        except Exception:
            return False

    def status(self) -> Dict[str, Any]:
        try:
            resolved_ids = self._resolve_sheet_ids()
        except Exception:
            resolved_ids = self.sheet_ids
        return {
            "configured": self.is_configured(),
            "sheets_folder_id": self.sheet_folder_id,
            "sheets_count": len(resolved_ids),
            "worksheets_count": len(self._cache),
            "resolved_sheet_ids": resolved_ids,
            "loaded": {k: len(v) for k, v in self._cache.items()},
            "debug": {"last_errors": self._last_errors[-8:]},
        }
