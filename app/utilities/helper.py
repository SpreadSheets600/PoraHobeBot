import io
import re

import requests
from flask import current_app
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from werkzeug.utils import secure_filename


def extract_drive_id(url: str):
    patterns = [
        r"/d/([a-zA-Z0-9-_]+)",
        r"id=([a-zA-Z0-9-_]+)",
        r"uc\?id=([a-zA-Z0-9-_]+)",
    ]
    for p in patterns:
        match = re.search(p, url)
        if match:
            return match.group(1)
    return None


def process_drive_link(drive_url, user):
    file_id = extract_drive_id(drive_url)
    if not file_id:
        raise ValueError("Invalid Or Unsupported Google Drive URL Format")

    public_download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        response = requests.get(public_download_url, stream=True, timeout=10)
        if response.status_code == 200:
            content = response.content
            filename = (
                response.headers.get("Content-Disposition", "")
                .split("filename=")[-1]
                .strip('"')
                or f"drive_file_{file_id}"
            )
            filename = secure_filename(filename)
            mime_type = response.headers.get("Content-Type", "application/octet-stream")
            size = len(content)

            fh = io.BytesIO(content)
            fh.seek(0)

            return {
                "file": fh,
                "filename": filename,
                "mime_type": mime_type,
                "size": size,
                "file_id": file_id,
                "downloaded": True,
            }
    except requests.RequestException:
        pass

    oauth = user.oauth_accounts.filter_by(provider="google").first()
    if not oauth:
        return {
            "original_link": drive_url,
            "downloaded": False,
        }

    creds = Credentials(
        token=oauth.token.get("access_token"),
        refresh_token=oauth.token.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=current_app.config["GOOGLE_CLIENT_ID"],
        client_secret=current_app.config["GOOGLE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )

    service = build("drive", "v3", credentials=creds)

    try:
        metadata = (
            service.files().get(fileId=file_id, fields="name, mimeType, size").execute()
        )
        filename = secure_filename(metadata["name"])
        mime_type = metadata["mimeType"]

        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()

        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)

        return {
            "file": fh,
            "filename": filename,
            "mime_type": mime_type,
            "size": metadata.get("size"),
            "file_id": file_id,
            "downloaded": True,
        }
    except Exception:
        return {
            "original_link": drive_url,
            "downloaded": False,
        }
