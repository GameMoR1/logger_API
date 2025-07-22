from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
from .gdrive_logger import GDriveLogger
from .constants import *
import threading
import os

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
    with lock:
        log_stats.append({
            'received_at': log_entry['received_at'],
            'filename': log_entry['filename']
        })
        log_files.append(log_entry)  # Сохраняем для UI
    threading.Thread(target=logger.log, args=(log_entry,)).start()
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
    return JSONResponse(content={
        "total_files": total_files,
        "total_duration": total_duration
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
        all_logs = logger.list_all_logs()
        files = []
        stats = []
        import tempfile
        for log_meta in all_logs:
            file_id = log_meta['id']
            name = log_meta['name']
            # Скачиваем во временный файл
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
                tmp_path = tmp.name
            try:
                data = None
                logger.download_log_file(file_id, tmp_path)
                data = logger.parse_log_file(tmp_path)
                # Приведение типов для числовых полей
                for key in ["duration", "queue_time", "process_time"]:
                    try:
                        data[key] = float(data[key])
                    except Exception:
                        data[key] = 0.0
                try:
                    data["size"] = int(data["size"])
                except Exception:
                    data["size"] = 0
                data['file_id'] = file_id  # сохраняем id файла
                files.append(data)
                if 'received_at' in data and 'filename' in data:
                    stats.append({'received_at': data['received_at'], 'filename': data['filename'], 'file_id': file_id})
            except Exception as e:
                print(f"[Google Drive ERROR]: Не удалось скачать/распарсить {name}: {e}")
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
        with lock:
            log_files = files
            log_stats = stats
    except Exception as e:
        print(f"[Google Drive ERROR]: Ошибка инициализации состояния: {e}")

# Инициализация при старте
if CREDENTIALS_EXISTS:
    threading.Thread(target=initialize_state_from_gdrive, daemon=True).start()

# --- Endpoint для удаления лога ---
from fastapi import Query
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
    # Удаляем из локального состояния
    with lock:
        log_files[:] = [l for l in log_files if l.get('file_id') != file_id]
        log_stats[:] = [s for s in log_stats if s.get('file_id') != file_id]
    return {"status": "deleted"}
