import json
import aiohttp
import asyncio
import requests
from pathlib import Path
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config import TOKEN_FILE, AUDIO_EXTENSIONS
from loguru import logger

def get_drive_service():
    try:
        if not TOKEN_FILE.exists():
            raise RuntimeError("No token file. Please go through it first. /auth/google и /auth/callback")

        with TOKEN_FILE.open("r", encoding="utf-8") as f:
            token_data = json.load(f)

        creds = Credentials(
            token=token_data["token"],
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=token_data["scopes"],
        )

        service = build("drive", "v3", credentials=creds)
        return service
    except Exception as e:
        logger.error(f"[ERROR] Failed to get drive service: {e}")
        raise e

def refresh_access_token(client_id, client_secret, refresh_token):
    try:
        url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        r = requests.post(url, data=data)
        r.raise_for_status()
        return r.json()["access_token"]

        cred_path = Path(TOKEN_FILE)

        with open(cred_path, "r", encoding="utf-8") as f:
            creds = json.load(f)

        new_token = refresh_access_token(
            creds["client_id"],
            creds["client_secret"],
            creds["refresh_token"]
        )
        creds["token"] = new_token

        with open(cred_path, "w", encoding="utf-8") as f:
            json.dump(creds, f, indent=4)

    except Exception as e:
        logger.error(f"[ERROR] Failed to refresh access token: {e}")
        return None

def list_items_in_folder(service, folder_id):
    try:
        items = []
        page_token = None

        while True:
            resp = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="nextPageToken, files(id, name, mimeType)",
                pageToken=page_token,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            ).execute()

            items.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        return items

    except Exception as e:
        logger.error(f"[ERROR] Failed to list items in folder {folder_id}: {e}")
        return []


def is_folder(item):
    return item['mimeType'] == 'application/vnd.google-apps.folder'

def is_audio_file(item):
    ext = Path(item['name']).suffix.lower()
    return ext in AUDIO_EXTENSIONS


async def upload_file_aio(drive_service, file_path, folder_id):
    try:

        file_metadata = {
            'name': file_path.name,
            'parents': [folder_id]
        }

        media = MediaFileUpload(file_path, resumable=True)
        loop = asyncio.get_event_loop()
        file = await loop.run_in_executor(
            None,
            lambda: drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name'
            ).execute()
        )
        return file
    except Exception as e:
        logger.error(f"[ERROR] Failed to upload file {file_path}: {e}")
        raise e


async def download_file_drive_api(file_id: str, dest_path: Path, access_token: str,
                                  client_id: str, client_secret: str, refresh_token: str):
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

        for attempt in range(2):
            try:
                headers = {"Authorization": f"Bearer {access_token}"}
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as resp:
                        if resp.status == 401:
                            raise aiohttp.ClientResponseError(
                                request_info=resp.request_info,
                                history=resp.history,
                                status=401,
                                message="Unauthorized",
                                headers=resp.headers
                            )

                        resp.raise_for_status()
                        content_type = resp.headers.get("Content-Type", "")
                        if "text/html" in content_type.lower():
                            text = await resp.text()
                            dest_path.with_suffix(".html").write_text(text, encoding="utf-8")
                            return False

                        with open(dest_path, "wb") as f:
                            async for chunk in resp.content.iter_chunked(1024 * 1024):
                                f.write(chunk)
                return True

            except aiohttp.ClientResponseError as e:
                if e.status == 401 and attempt == 0:
                    logger.info(f"[INFO] Access token expired, refreshing...")
                    access_token = refresh_access_token(client_id, client_secret, refresh_token)
                else:
                    logger.error(f"[ERROR] Failed to download {dest_path.name}: {e}")
                    return False

    except Exception as e:
        logger.error(f"[ERROR] Exception in download_file_drive_api for {dest_path.name}: {e}")
        return False


async def download_all_items_drive_api(
    items,
    dest_folder: Path,
    access_token: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    max_concurrent: int = 3
):
    try:
        semaphore = asyncio.Semaphore(max_concurrent)
        downloaded_files: list[Path] = []
        skipped_files: list[Path] = []

        async def sem_download(item):
            async with semaphore:
                file_id = item["id"]
                filename = item["name"]
                dest_path = dest_folder / filename

                success = await download_file_drive_api(file_id, dest_path, access_token, client_id, client_secret, refresh_token)
                if success:
                    downloaded_files.append(dest_path)
                else:
                    skipped_files.append(dest_path)

        await asyncio.gather(*(sem_download(item) for item in items))
        return downloaded_files
    except Exception as e:
        logger.error(f"[ERROR] Exception in download_all_items_drive_api: {e}")
        raise e

async def upload_transcribed_files(drive_service, transcribed_files, folder_id):
    try:
        uploaded_items = []
        for file_path in transcribed_files:
            uploaded = await upload_file_aio(drive_service, Path(file_path), folder_id)
            uploaded_items.append(uploaded)
        return uploaded_items

    except Exception as e:
        logger.error(f"[ERROR] Failed to upload transcribed files: {e}")
        raise e

def create_folder(service, folder_name: str, parent_id: str | None = None) -> dict:
    try:
        folder_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        if parent_id:
            folder_metadata["parents"] = [parent_id]

        folder = (
            service.files()
            .create(body=folder_metadata, fields="id, name, parents")
            .execute()
        )

        return folder
    except Exception as e:
        logger.error(f"[ERROR] Failed to create folder '{folder_name}': {e}")
        raise e


def move_file_to_folder(service, file_item, target_folder_id):
    try:
        file_id = file_item["id"]
        file = service.files().get(fileId=file_id, fields="parents").execute()
        prev_parents = ",".join(file.get("parents", []))

        updated = service.files().update(
            fileId=file_id,
            addParents=target_folder_id,
            removeParents=prev_parents,
            fields="id, parents",
        ).execute()

        return updated
    except Exception as e:
        logger.error(f"[ERROR] Failed to move file {file_item.get('name')}: {e}")
        raise e

def move_audio_recursively(service, source_folder_id, target_folder_id):
    try:
        list_item = []
        items = list_items_in_folder(service, source_folder_id)
        for item in items:
            if is_folder(item):
                move_audio_recursively(service, item["id"], target_folder_id)
            elif is_audio_file(item):
                move_file_to_folder(service, item, target_folder_id)
                list_item.append(item)
        return list_item

    except Exception as e:
        logger.error(f"[ERROR] Failed to move audio recursively from {source_folder_id}: {e}")
        raise e
