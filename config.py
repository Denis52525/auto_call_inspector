import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(override=True)

AUDIO_EXTENSIONS = os.getenv("AUDIO_EXTENSIONS")
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR")
CLIENT_SECRET_FILE = Path(os.getenv("CLIENT_SECRET_FILE"))
TOKEN_FILE = Path(os.getenv("TOKEN_FILE"))
# Ollama настройки
MODEL_URL = os.getenv("MODEL_URL")
MODEL_NAME = os.getenv("MODEL_NAME")
TEMPERATURE = os.getenv("TEMPERATURE")
REDIRECT_URI = "http://localhost:8000/auth/callback"
MAX_SEGMENT_LENGTH = int(os.getenv("MAX_SEGMENT_LENGTH"))
SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
SHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME")