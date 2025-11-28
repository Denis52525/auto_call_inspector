import json
from fastapi import FastAPI, Request
from google_auth_oauthlib.flow import Flow
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from loguru import logger
from pathlib import Path
from drive_file_manager import create_folder, move_audio_recursively, get_drive_service, \
     upload_transcribed_files, download_all_items_drive_api
from config import CLIENT_SECRET_FILE, REDIRECT_URI, TOKEN_FILE, WORKSPACE_DIR
from call_analysis import process_transcript_file
from google_sheets_reports import push_daily_report, extract_date_and_phone
from transcribe_audio import process_audio_file, yes_no_to_binary

logger.add("app_logs.log", rotation="10 MB", retention="7 days")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/auth/google")
async def auth_google():
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=["https://www.googleapis.com/auth/drive"],
            redirect_uri=REDIRECT_URI,
        )

        auth_url, state = flow.authorization_url()

        return JSONResponse(status_code=200, content={"auth_url": auth_url})
    except Exception as e:
        logger.error(f"Error in API endpoint /auth/google : {e}")
        return JSONResponse(status_code=500, content={"result": str(e)})


@app.get("/auth/callback")
async def auth_callback(request: Request):
    try:
        state = request.query_params.get("state")
        code = request.query_params.get("code")

        if not code:
            return JSONResponse(status_code=400, content={"error": "no_code"})

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=["https://www.googleapis.com/auth/drive"],
            redirect_uri=REDIRECT_URI,
            state=state,
        )

        flow.fetch_token(code=code)

        creds = flow.credentials


        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=4)

        return JSONResponse(status_code=200, content={"status": "ok"})
    except Exception as e:
        logger.error(f"Error in API endpoint /auth/callback : {e}")
        return JSONResponse(status_code=500, content={"result": str(e)})


@app.get("/start")
async def start(request: Request, folder_id: str):
    try:
        drive = get_drive_service()
        workspace_dir = Path(WORKSPACE_DIR)

        workspace_dir.mkdir(parents=True, exist_ok=True)
        target_folder = create_folder(drive, WORKSPACE_DIR)
        items = move_audio_recursively(drive, folder_id, target_folder['id'])

        with open("credentials.json", "r", encoding="utf-8") as f:
            creds = json.load(f)

        access_token = creds.get("token")
        refresh_token = creds.get("refresh_token")
        client_id = creds.get("client_id")
        client_secret = creds.get("client_secret")
        downloaded_files = await download_all_items_drive_api(items, workspace_dir, access_token, client_id, client_secret, refresh_token)

        for audio_file in downloaded_files:
            try:
                if audio_file.suffix.lower() != ".mp3":
                    continue

                transcribed_files = process_audio_file(audio_file)
                audio_file.unlink()

                await upload_transcribed_files(drive, transcribed_files, target_folder['id'])

                for transcribed_file in transcribed_files:
                    try:
                        file_path = Path(transcribed_file)
                        if file_path.suffix.lower() != ".txt":
                            continue
                        result = process_transcript_file(transcribed_file)
                        date, phone = extract_date_and_phone(file_path)
                        push_daily_report(
                            date,
                            result[0].get("Тип звернення", "Інше"),
                            f"+380{phone}",
                            "",
                            "",
                            result[0].get("Початок розмови, представлення"),
                            result[0].get("Чи дізнвся менеджер кузов атвомобіля"),
                            result[0].get("Чи дізнався менеджер рік автомобіля"),
                            result[0].get("Чи дізнався менеджр пробіг"),
                            result[0].get("Пропозиція про комплексну діагностику"),
                            result[0].get("Дізнався які роботи робилися раніше"),
                            result[0].get("Запис на сервіс, Дата"),
                            result[0].get("Завершення розмови прощання"),
                            result[2].get("Яка робота з топ 100"),
                            yes_no_to_binary(result[1].get("Чи дотримувався всіх інструкцій з топ 100 робіт Да/Ні")),
                            result[1].get("Яких рекоменадцій менеджер не дотримувався з топ 100 робіт"),
                            result[1].get("Результат", "Інше"),
                            "",
                            result[1].get("Запчастини", "Наші"),
                            result[0].get("Коментарий"),
                        )
                        file_path.unlink()
                    except Exception as e:
                        logger.error(f"Error while processing {transcribed_file.name}: {e}")
            except Exception as e:
                logger.error(f"Error while processing {audio_file.name}: {e}")


        return JSONResponse(status_code=200, content={"status": "ok"})
    except Exception as e:
        logger.error(f"Error in API endpoint /start : {e}")
        return JSONResponse(status_code=500, content={"result": str(e)})

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)