"""
Google Drive API Client for searching and fetching AI Studio chat files.
"""

import os
import io
import sys
from typing import Optional, List, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from utils.drive.auth import get_drive_credentials

DEFAULT_FOLDER_NAME = "Google AI Studio"


class GoogleDriveChatFetcher:
    def __init__(self, credentials=None):
        self.creds = credentials or get_drive_credentials()
        self.service = build('drive', 'v3', credentials=self.creds)

    def resolve_folder_id(self, folder_name: str = DEFAULT_FOLDER_NAME) -> Optional[str]:
        """Resolves folder ID by folder name."""
        env_folder_id = os.environ.get("GDRIVE_STUDIO_FOLDER_ID")
        if env_folder_id:
            return env_folder_id

        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        try:
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])
            if files:
                return files[0]['id']
        except HttpError as e:
            print(f"Error querying Google Drive folder '{folder_name}': {e}", file=sys.stderr)
        return None

    def search_chat_files(self, chat_name: str, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Searches for chat files matching name inside the specified folder."""
        if not folder_id:
            folder_id = self.resolve_folder_id()

        q_parts = [f"name contains '{chat_name}'", "trashed = false"]
        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")

        query = " and ".join(q_parts)
        try:
            results = self.service.files().list(
                q=query,
                fields="files(id, name, modifiedTime, size, mimeType)"
            ).execute()
            return results.get('files', [])
        except HttpError as e:
            if e.resp.status in (401, 403):
                raise RuntimeError(
                    f"Google Drive Authorization Error ({e.resp.status}): {e}. "
                    "Check GDRIVE_REFRESH_TOKEN or credentials permissions."
                ) from e
            raise RuntimeError(f"Google Drive API query error: {e}") from e

    def fetch_chat_file(self, chat_name: str, output_dir: str = "input_data", folder_id: Optional[str] = None) -> str:
        """
        Finds matching chat file and downloads raw bytes to output_dir.
        If multiple candidates exist, prints candidate list and raises RuntimeError.
        """
        candidates = self.search_chat_files(chat_name, folder_id=folder_id)

        if not candidates:
            raise FileNotFoundError(f"No file matching chat name '{chat_name}' found on Google Drive.")

        if len(candidates) > 1:
            msg = [f"Multiple files matching '{chat_name}' found on Google Drive:"]
            for c in candidates:
                msg.append(f" - ID: {c['id']} | Name: {c['name']} | Modified: {c.get('modifiedTime')}")
            msg.append("Please specify a more exact chat name.")
            raise RuntimeError("\n".join(msg))

        target_file = candidates[0]
        file_id = target_file['id']
        file_name = target_file['name']

        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, file_name)

        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        finished = False
        while not finished:
            status, finished = downloader.next_chunk()

        with open(out_path, 'wb') as f:
            f.write(fh.getvalue())

        return out_path
