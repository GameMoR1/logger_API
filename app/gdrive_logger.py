import os
from datetime import datetime
from typing import Dict
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from .constants import *
import json
import tempfile
import uuid

SCOPES = ['https://www.googleapis.com/auth/drive.file']

INDEX_FILENAME = 'logs_index.json'

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

    def _get_or_create_index_file(self):
        """
        Возвращает file_id индекс-файла logs_index.json в LogerAPI_Logs на Google Диске или создаёт его, если нет.
        """
        # Убедиться, что корневая папка существует
        root_folder_id = self._get_or_create_root_folder()
        query = f"name='{INDEX_FILENAME}' and '{root_folder_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        if items:
            return items[0]['id']
        # Создать пустой индекс-файл именно в LogerAPI_Logs
        tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        try:
            with open(tmpfile.name, 'w', encoding='utf-8') as f:
                json.dump([], f)
            file_metadata = {
                'name': INDEX_FILENAME,
                'parents': [root_folder_id],
                'mimeType': 'application/json'
            }
            media = MediaFileUpload(tmpfile.name, mimetype='application/json')
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            return file.get('id')
        except Exception as e:
            print(f'[Google Drive ERROR]: Не удалось создать индекс-файл: {e}')
            raise
        finally:
            try:
                os.remove(tmpfile.name)
            except Exception:
                pass

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

    def log_and_return_id(self, data: Dict):
        date_str = datetime.now().strftime(DATE_FORMAT)
        folder_id = self._get_or_create_day_folder(date_str)
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
        file_id = None
        try:
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            file_id = file.get('id')
        except Exception as e:
            print(f"[Google Drive ERROR]: {e}")
        finally:
            import time
            for _ in range(10):
                try:
                    os.remove(local_path)
                    break
                except PermissionError:
                    time.sleep(0.1)
            else:
                print(f"[Google Drive ERROR]: Не удалось удалить временный файл {local_path}")
        return file_id

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

    def load_index(self):
        """
        Загружает и возвращает список логов из индекс-файла.
        """
        file_id = self._get_or_create_index_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmpfile:
            local_path = tmpfile.name
        try:
            self.download_log_file(file_id, local_path)
            with open(local_path, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
        finally:
            try:
                os.remove(local_path)
            except Exception:
                pass

    def save_index(self, index_data):
        """
        Сохраняет index_data (list) в индекс-файл на Google Drive.
        """
        file_id = self._get_or_create_index_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmpfile:
            local_path = tmpfile.name
        try:
            with open(local_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False)
            media = MediaFileUpload(local_path, mimetype='application/json')
            self.service.files().update(fileId=file_id, media_body=media).execute()
        finally:
            try:
                os.remove(local_path)
            except Exception:
                pass

    def add_log_to_index(self, log_entry):
        index = self.load_index()
        index.append(log_entry)
        self.save_index(index)

    def remove_log_from_index(self, file_id):
        index = self.load_index()
        index = [item for item in index if item.get('file_id') != file_id]
        self.save_index(index)

    def sync_index_with_drive(self):
        """
        Проверяет наличие и целостность logs_index.json на Google Диске, если повреждён или отсутствует — пересоздаёт.
        """
        try:
            file_id = self._get_or_create_index_file()
            # Пробуем скачать и прочитать файл
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmpfile:
                local_path = tmpfile.name
            try:
                self.download_log_file(file_id, local_path)
                with open(local_path, encoding='utf-8') as f:
                    json.load(f)  # Проверка на валидность
            except Exception as e:
                print(f'[Google Drive ERROR]: Индекс-файл повреждён, пересоздаём: {e}')
                self.save_index([])  # Пересоздать пустой
            finally:
                try:
                    os.remove(local_path)
                except Exception:
                    pass
        except Exception as e:
            print(f'[Google Drive ERROR]: Не удалось синхронизировать индекс-файл: {e}')

    def ensure_index_consistency(self):
        """
        Гарантирует, что индекс-файл на Google Диске существует и валиден при запуске.
        """
        self.sync_index_with_drive()

    def save_last_online(self, dt_str):
        """
        Сохраняет время последнего онлайна в файл last_online.txt в ту же папку, что и logs_index.json
        """
        from io import BytesIO
        # Получаем parent folder id из index-файла
        index_file_id = self.find_file_id_by_name('logs_index.json')
        parent_id = None
        if index_file_id:
            # Получаем родительскую папку
            file = self.drive_service.files().get(fileId=index_file_id, fields='parents').execute()
            parents = file.get('parents', [])
            if parents:
                parent_id = parents[0]
        file_metadata = {
            'name': 'last_online.txt',
            'mimeType': 'text/plain'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
        media = BytesIO(dt_str.encode('utf-8'))
        file_id = self.find_file_id_by_name('last_online.txt')
        if file_id:
            self.drive_service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
        else:
            self.drive_service.files().create(
                body=file_metadata,
                media_body=media
            ).execute()

    def find_file_id_by_name(self, filename):
        """
        Возвращает file_id файла по имени, если найден, иначе None
        """
        results = self.drive_service.files().list(q=f"name='{filename}' and trashed=false", fields="files(id)").execute()
        files = results.get('files', [])
        return files[0]['id'] if files else None
