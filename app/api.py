from fastapi import FastAPI, Request, Body, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
from .gdrive_logger import GDriveLogger
from .constants import *
import threading
import os
import importlib.util
import sys
import subprocess
import requests

app = FastAPI()
app.mount('/static', StaticFiles(directory='app/static'), name='static')

# Проверка наличия credentials.json
CREDENTIALS_EXISTS = os.path.exists(GOOGLE_CREDENTIALS_FILE)
ERROR_MESSAGE = None if CREDENTIALS_EXISTS else 'Файл credentials.json не найден. Работа невозможна.'

logger = None  # Не инициализируем сразу

log_stats = []
log_files = []  # Для хранения информации о логах
lock = threading.Lock()

class LogData(BaseModel):
    filename: str
    duration: float
    size: int
    received_at: str
    queue_time: float
    process_time: float
    text: str

@app.post('/log')
async def log_file(data: LogData):
    global logger
    if not CREDENTIALS_EXISTS:
        return JSONResponse(content={"error": ERROR_MESSAGE}, status_code=500)
    if logger is None:
        try:
            logger = GDriveLogger()
        except Exception as e:
            return JSONResponse(content={"error": f"Ошибка инициализации GDriveLogger: {e}"}, status_code=500)
    log_entry = data.dict()
    # Приведение типов для числовых полей (на всякий случай)
    for key in ["duration", "queue_time", "process_time"]:
        try:
            log_entry[key] = float(log_entry[key])
        except Exception:
            log_entry[key] = 0.0
    try:
        log_entry["size"] = int(log_entry["size"])
    except Exception:
        log_entry["size"] = 0
    # Сохраняем лог в Google Drive и получаем file_id
    file_id = None
    def log_and_get_id():
        nonlocal file_id
        file_id = logger.log_and_return_id(log_entry)
    t = threading.Thread(target=log_and_get_id)
    t.start()
    t.join()
    log_entry['file_id'] = file_id
    # Добавляем в индекс
    logger.add_log_to_index(log_entry)
    with lock:
        log_stats.append({
            'received_at': log_entry['received_at'],
            'filename': log_entry['filename'],
            'file_id': file_id
        })
        log_files.append(log_entry)
    return {'status': 'ok'}

@app.get('/stats')
async def get_stats():
    if not CREDENTIALS_EXISTS:
        return JSONResponse(content={"error": ERROR_MESSAGE}, status_code=500)
    stats = {}
    with lock:
        for entry in log_stats:
            t = entry['received_at'][:16]
            stats[t] = stats.get(t, 0) + 1
    return JSONResponse(content=stats)

@app.get('/histogram')
async def get_histogram():
    if not CREDENTIALS_EXISTS:
        return JSONResponse(content={"error": ERROR_MESSAGE}, status_code=500)
    histogram = {}
    with lock:
        for entry in log_stats:
            day = entry['received_at'][:10]
            histogram[day] = histogram.get(day, 0) + 1
    return JSONResponse(content=histogram)

@app.get('/logs')
async def get_logs(filename: str = None, date: str = None):
    if not CREDENTIALS_EXISTS:
        return JSONResponse(content={"error": ERROR_MESSAGE}, status_code=500)
    with lock:
        filtered = log_files
        if filename:
            filtered = [l for l in filtered if filename in l['filename']]
        if date:
            filtered = [l for l in filtered if l['received_at'].startswith(date)]
    # Возвращаем file_id для фронта
    return JSONResponse(content=filtered)

@app.get('/log_text')
async def get_log_text(filename: str, received_at: str):
    if not CREDENTIALS_EXISTS:
        return JSONResponse(content={"error": ERROR_MESSAGE}, status_code=500)
    with lock:
        for l in log_files:
            if l['filename'] == filename and l['received_at'] == received_at:
                return JSONResponse(content={"text": l['text']})
    return JSONResponse(content={"error": "Лог не найден"}, status_code=404)

@app.get('/summary')
async def get_summary():
    if not CREDENTIALS_EXISTS:
        return JSONResponse(content={"error": ERROR_MESSAGE}, status_code=500)
    with lock:
        total_files = len(log_files)
        total_duration = sum(l.get('duration', 0) for l in log_files)
        total_size = sum(l.get('size', 0) for l in log_files)
    return JSONResponse(content={
        "total_files": total_files,
        "total_duration": total_duration,
        "total_size": total_size
    })

@app.get('/', response_class=HTMLResponse)
async def index():
    with open('app/static/index.html', encoding='utf-8') as f:
        html = f.read()
    if not CREDENTIALS_EXISTS:
        html = html.replace('</body>', f'<div style="color:red;font-weight:bold;">{ERROR_MESSAGE}</div></body>')
    return HTMLResponse(html)

# --- Инициализация состояния из Google Drive ---
def initialize_state_from_gdrive():
    global logger, log_files, log_stats
    if not CREDENTIALS_EXISTS:
        return
    try:
        if logger is None:
            logger = GDriveLogger()
        # Проверка и синхронизация индекс-файла
        logger.ensure_index_consistency()
        # Загружаем только индекс-файл
        index = logger.load_index()
        files = []
        stats = []
        for entry in index:
            files.append(entry)
            if 'received_at' in entry and 'filename' in entry:
                stats.append({'received_at': entry['received_at'], 'filename': entry['filename'], 'file_id': entry.get('file_id')})
        with lock:
            log_files = files
            log_stats = stats
    except Exception as e:
        print(f"[Google Drive ERROR]: Ошибка инициализации состояния: {e}")

# Инициализация при старте
if CREDENTIALS_EXISTS:
    threading.Thread(target=initialize_state_from_gdrive, daemon=True).start()

# --- Endpoint для удаления лога ---
@app.delete('/log')
async def delete_log(file_id: str = Query(...)):
    global logger
    if not CREDENTIALS_EXISTS:
        return JSONResponse(content={"error": ERROR_MESSAGE}, status_code=500)
    if logger is None:
        try:
            logger = GDriveLogger()
        except Exception as e:
            return JSONResponse(content={"error": f"Ошибка инициализации GDriveLogger: {e}"}, status_code=500)
    # Удаляем с Google Drive
    logger.delete_log_file(file_id)
    # Удаляем из индекс-файла
    logger.remove_log_from_index(file_id)
    # Удаляем из локального состояния
    with lock:
        log_files[:] = [l for l in log_files if l.get('file_id') != file_id]
        log_stats[:] = [s for s in log_stats if s.get('file_id') != file_id]
    return {"status": "deleted"}

CONFIG_PATH = '../whisper_API_que/core/config.py'  # путь к файлу в другом репозитории
CONFIG_GITHUB_URL = 'https://raw.githubusercontent.com/GameMoR1/whisper_API_que/main/core/config.py'

# --- API для настроек ---
@app.get('/api/settings')
async def get_settings():
    # Всегда грузим из GitHub
    try:
        resp = requests.get(CONFIG_GITHUB_URL, timeout=5)
        if resp.status_code == 200:
            code = resp.text
            result = {}
            for line in code.splitlines():
                if line.strip().startswith('MODEL_NAMES'):
                    result['modelNames'] = eval(line.split('=',1)[1].strip(), {}, {})
                elif line.strip().startswith('WEBHOOK_INTERVAL'):
                    result['webhookInterval'] = int(line.split('=',1)[1].split('#')[0].strip())
                elif line.strip().startswith('WEBHOOK_ENABLED'):
                    result['webhookEnabled'] = 'True' in line
                elif line.strip().startswith('WEBHOOK_URL'):
                    result['webhookUrl'] = line.split('=',1)[1].strip().strip('"\'')
                elif line.strip().startswith('LOGGER_API_URL'):
                    result['loggerApiUrl'] = line.split('=',1)[1].strip().strip('"\'')
            return result
        else:
            return {'error': 'Не удалось загрузить config.py из GitHub'}
    except Exception as e:
        return {'error': f'Ошибка загрузки config.py из GitHub: {e}'}

@app.post('/api/settings')
async def save_settings(data: dict = Body(...)):
    import os
    if not os.path.isdir('../whisper_API_que') or not os.path.isdir('../whisper_API_que/.git'):
        return JSONResponse(content={'error': 'Локальный git-репозиторий ../whisper_API_que не найден. Склонируйте репозиторий перед сохранением.'}, status_code=500)
    text = f'''# Все основные константы для настройки сервиса\n\nMODEL_NAMES = {repr(data.get('modelNames', []))}\n\nWEBHOOK_INTERVAL = {int(data.get('webhookInterval', 600))}  # 10 минут\n\nWEBHOOK_ENABLED = {bool(data.get('webhookEnabled', True))}\n\nWEBHOOK_URL = {repr(data.get('webhookUrl', ''))}\n\nLOGGER_API_URL = {repr(data.get('loggerApiUrl', ''))}\n'''
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        f.write(text)
    try:
        subprocess.run(['git', '-C', '../whisper_API_que', 'add', 'core/config.py'], check=True)
        subprocess.run(['git', '-C', '../whisper_API_que', 'commit', '-m', 'Update config.py via web UI'], check=True)
        subprocess.run(['git', '-C', '../whisper_API_que', 'push'], check=True)
    except subprocess.CalledProcessError as e:
        return JSONResponse(content={'error': f'Ошибка git: {e}. Вывод: {e.output if hasattr(e, "output") else ""}'}, status_code=500)
    except Exception as e:
        return JSONResponse(content={'error': f'Ошибка git: {e}'}, status_code=500)
    return {'status': 'ok'}

@app.post('/api/settings/rollback')
async def rollback_settings():
    try:
        # Откатить последний коммит только для config.py
        subprocess.run(['git', '-C', '../whisper_API_que', 'checkout', 'HEAD~1', '--', 'core/config.py'], check=True)
        subprocess.run(['git', '-C', '../whisper_API_que', 'commit', '-am', 'Rollback config.py via web UI'], check=True)
        subprocess.run(['git', '-C', '../whisper_API_que', 'push'], check=True)
    except Exception as e:
        return JSONResponse(content={'error': f'Ошибка отката: {e}'}, status_code=500)
    return {'status': 'ok'}

@app.get('/settings', response_class=HTMLResponse)
async def settings_page():
    with open('app/static/settings.html', encoding='utf-8') as f:
        html = f.read()
    return HTMLResponse(html)
