# config.py para AlphaBot
# Centraliza leitura de segredos/env para integração com SheetsLoader e chatbot
import os
import streamlit as st
from google.oauth2 import service_account

def get_abacus_api_key() -> str:
    return st.secrets.get("ABACUS_API_KEY", "") or os.getenv("ABACUS_API_KEY", "")

def get_model_name(default: str = "gemini-2.5-pro") -> str:
    return st.secrets.get("MODEL_NAME", default) or os.getenv("MODEL_NAME", default)

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

def get_sheets_ids() -> list[str]:
    ids = st.secrets.get("SHEETS_IDS", "") or os.getenv("SHEETS_IDS", "")
    return [i.strip() for i in ids.split(",") if i.strip()]

def get_sheet_range(default: str = "A:Z") -> str:
    return st.secrets.get("SHEET_RANGE", default) or os.getenv("SHEET_RANGE", default)

def get_service_account_email() -> str:
    info = st.secrets.get("google_service_account")
    if info:
        return info.get("client_email", "")
    return ""
