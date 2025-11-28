from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from config import SCOPES_SHEETS, SERVICE_ACCOUNT_FILE, SHEET_ID, SHEET_NAME
from loguru import logger


def push_daily_report(
    date: str,
    request_type: str,
    phone: str,
    branch: str,
    manager: str,
    intro: int,
    car_body_known: int,
    car_year_known: int,
    mileage_known: int,
    complex_diagnosis_offer: int,
    previous_works_known: int,
    service_date: str,
    farewell: int,
    top100_work: str,
    followed_all_instructions: int,
    which_recommendations_not_followed: str,
    result: str,
    score: str,
    spare_parts: str,
    comment: str,
):
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES_SHEETS)
        service = build("sheets", "v4", credentials=creds)

        sheet_metadata = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        sheet_info = next(sheet for sheet in sheet_metadata["sheets"] if sheet["properties"]["title"] == SHEET_NAME)
        sheet_id_num = sheet_info["properties"]["sheetId"]


        insert_requests = [
            {"insertDimension": {
                "range": {
                    "sheetId": sheet_id_num,
                    "dimension": "ROWS",
                    "startIndex": 2,
                    "endIndex": 3
                },
                "inheritFromBefore": False
            }}
        ]
        service.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body={"requests": insert_requests}).execute()

        copy_requests = [
            {"copyPaste": {
                "source": {"sheetId": sheet_id_num, "startRowIndex": 64, "endRowIndex": 65},
                "destination": {"sheetId": sheet_id_num, "startRowIndex": 2, "endRowIndex": 3},
                "pasteType": "PASTE_FORMAT"
            }},
            {"copyPaste": {
                "source": {"sheetId": sheet_id_num, "startRowIndex": 64, "endRowIndex": 65},
                "destination": {"sheetId": sheet_id_num, "startRowIndex": 2, "endRowIndex": 3},
                "pasteType": "PASTE_DATA_VALIDATION"
            }}
        ]

        service.spreadsheets().batchUpdate(
            spreadsheetId=SHEET_ID,
            body={"requests": copy_requests}
        ).execute()

        row_values = [
            date,
            request_type,
            phone,
            branch,
            manager,
            intro,
            car_body_known,
            car_year_known,
            mileage_known,
            complex_diagnosis_offer,
            previous_works_known,
            service_date,
            farewell,
            top100_work,
            followed_all_instructions,
            which_recommendations_not_followed,
            result,
            score,
            spare_parts,
            comment,
        ]
        write_range = f"{SHEET_NAME}!A3"
        body = {"values": [row_values]}
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=write_range,
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()

    except Exception as e:
        logger.error(f"Error: {e}")
        raise e

def extract_date_and_phone(file_path: Path):
    try:
        file_name = (file_path).stem
        parts = file_name.split("_")
        date = parts[0]
        phone = parts[2]
        return date, phone
    except Exception as e:
        logger.error(f"Error: {e}")
        raise e