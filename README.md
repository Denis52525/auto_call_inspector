# Auto Call Inspector

An automated tool for downloading audio files from Google Drive, transcribing calls, and generating reports in Google Sheets.

This project is designed to analyze client calls, evaluate manager performance, and log transcription results in a spreadsheet.

## Key Features
- Download audio files from a specified Google Drive folder.
- Copy audio files to the project workspace.
- Transcribe audio files and save the results alongside the audio files.
- Extract data from transcription results, including date, phone number, and call type, and log it into a Google Sheet.
- Automatically evaluate manager performance during calls.

## Requirements

- Python 3.10+
- FastAPI
- Google Drive API & Google Sheets API
- Docker

## Project Setup

1. Create a `.env` file based on `.env.example`.

2. Create a project in Google Cloud:
   - Create a service account and download `google_service_account.json` to the project root.
   - Add the service account email as an editor to the Google Sheet.
   - Enable APIs: **Google Drive API** and **Google Sheets API**.
   - Create an OAuth 2.0 Client ID (Desktop Client) and save as `client_secrets.json`.
   - Add your main email to the Google Auth Platform for authentication.

---

## Installation & Running

### Using Docker Compose

Docker is required for this project because the Ollama server and AI model `qwen2.5:3b` run inside the container.

```bash
docker-compose build
docker-compose up -d
```

> **Note:** The container automatically:
> 
> - Starts the Ollama server.
> - Waits 5 seconds for the server to be ready.
> - Pulls the model `qwen2.5:3b`.
> - Keeps the container running.

## Manual Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd <repository-name>
```

### 2. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Start the FastAPI server
```bash
python main.py
```
Important: Make sure the Docker container with Ollama is running before starting the FastAPI server, otherwise the AI model will not be available.

# API Endpoints

| Endpoint               | Method | Description                                      |
|------------------------|--------|--------------------------------------------------|
| /auth/google           | GET    | Request Google OAuth authorization              |
| /auth/callback         | GET    | Callback after authorization; saves tokens     |
| /start?folder_id=...   | GET    | Start the process: download, transcribe, and log data to Google Sheets |

> **Note about `folder_id`:**  
> The `folder_id` parameter specifies the Google Drive folder containing the audio files you want to process.  
> For example, for this folder:  
> [https://drive.google.com/drive/u/0/folders/45bZHTOGf4rndsf9knrR4F42_bW5gFma0](https://drive.google.com/drive/u/0/folders/45bZHTOGf4rndsf9knrR4F42_bW5gFma0)  
> the `folder_id` is:  
> `45bZHTOGf4rndsf9knrR4F42_bW5gFma0`

## Notes

- All errors are logged in `app_logs.log`.
- Audio files are deleted from the workspace after transcription.
- Make sure Google Drive and Google Sheets access is properly configured before running the project.
