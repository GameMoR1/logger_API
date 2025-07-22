import os
from datetime import datetime
from typing import Dict
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from .constants import *

SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GDriveLogger:
    def __init__(self):
        self.creds = self.get_user_credentials()
        self.service = build('drive', 'v3', credentials=self.creds)
        self.root_folder_id = self._get_or_create_root_folder()

    def get_user_credentials(self):
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        return creds

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
        # Исправление: убираем двоеточие и пробелы из received_at для имени файла
        safe_received_at = data['received_at'].replace(':', '-').replace(' ', '_')
        filename = f"{data['filename']}_{safe_received_at}{LOG_FILE_EXTENSION}"
        local_path = f"/tmp/{filename}"
        with open(local_path, 'w', encoding='utf-8') as f:
            for k, v in data.items():
                f.write(f"{k}: {v}\n")
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        media = MediaFileUpload(local_path, mimetype='text/plain')
        try:
            self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        except Exception as e:
            print(f"[Google Drive ERROR]: {e}")
        finally:
            # Исправление: безопасное удаление файла (ждём, пока файл не освободится)
            import time
            for _ in range(10):
                try:
                    os.remove(local_path)
                    break
                except PermissionError:
                    time.sleep(0.1)
            else:
                print(f"[Google Drive ERROR]: Не удалось удалить временный файл {local_path}")

    def list_all_logs(self):
        """
        Возвращает список всех лог-файлов (метаданные) из всех папок-дней в корневой папке.
        """
        # Получаем все папки-даты
        query = f"'{self.root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        day_folders = self.service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
        all_logs = []
        for folder in day_folders:
            folder_id = folder['id']
            date_str = folder['name']
            # Получаем все .txt файлы в папке-дне
            q = f"'{folder_id}' in parents and mimeType='text/plain' and trashed=false"
            files = self.service.files().list(q=q, fields="files(id, name)").execute().get('files', [])
            for f in files:
                all_logs.append({
                    'id': f['id'],
                    'name': f['name'],
                    'date': date_str
                })
        return all_logs

    def download_log_file(self, file_id, local_path):
        """
        Скачивает файл с Google Drive по file_id в local_path.
        """
        from googleapiclient.http import MediaIoBaseDownload
        import io
        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(local_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.close()

    def parse_log_file(self, local_path):
        """
        Парсит локальный лог-файл в dict. Приводит duration, size, queue_time, process_time к числам.
        """
        data = {}
        with open(local_path, encoding='utf-8') as f:
            for line in f:
                if ':' in line:
                    k, v = line.strip().split(':', 1)
                    data[k.strip()] = v.strip()
        # Приведение типов
        for key in ["duration", "queue_time", "process_time"]:
            if key in data:
                try:
                    data[key] = float(data[key])
                except Exception:
                    data[key] = 0.0
        if "size" in data:
            try:
                data["size"] = int(data["size"])
            except Exception:
                data["size"] = 0
        return data

    def delete_log_file(self, file_id):
        """
        Удаляет файл с Google Drive по file_id.
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
        except Exception as e:
            print(f"[Google Drive ERROR]: Не удалось удалить файл {file_id}: {e}")
