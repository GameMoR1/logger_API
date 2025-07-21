import os
from datetime import datetime
from typing import Dict
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
from .constants import *

class GDriveLogger:
    def __init__(self):
        self.creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=['https://www.googleapis.com/auth/drive'])
        self.service = build('drive', 'v3', credentials=self.creds)
        self.root_folder_id = self._get_or_create_root_folder()

    def _get_or_create_root_folder(self):
        query = f"name='{GOOGLE_DRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        if items:
            return items[0]['id']
        file_metadata = {
            'name': GOOGLE_DRIVE_FOLDER_NAME,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = self.service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

    def _get_or_create_day_folder(self, date_str: str):
        query = f"name='{date_str}' and mimeType='application/vnd.google-apps.folder' and '{self.root_folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        if items:
            return items[0]['id']
        file_metadata = {
            'name': date_str,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [self.root_folder_id]
        }
        folder = self.service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

    def log(self, data: Dict):
        date_str = datetime.now().strftime(DATE_FORMAT)
        folder_id = self._get_or_create_day_folder(date_str)
        filename = f"{data['filename']}_{data['received_at']}{LOG_FILE_EXTENSION}"
        local_path = f"/tmp/{filename}"
        with open(local_path, 'w', encoding='utf-8') as f:
            for k, v in data.items():
                f.write(f"{k}: {v}\n")
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        media = MediaFileUpload(local_path, mimetype='text/plain')
        self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        os.remove(local_path)
