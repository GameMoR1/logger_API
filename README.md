# LogerAPI

FastAPI-сервис для логирования информации о файлах и сохранения логов на Google Диск. Веб-интерфейс отображает статистику поступления файлов в реальном времени.

## Возможности
- Приём POST-запросов с данными о файле (без самого файла)
- Сохранение логов в Google Drive, разложенных по папкам по дате
- Каждый лог хранится с уникальным file_id (Google Drive id), что гарантирует корректное удаление и работу с дубликатами
- Веб-интерфейс с двумя графиками (по минутам и по дням), фильтрами, просмотром логов, удалением по кнопке
- Современный тёмный UI (HTML/CSS/JS, Chart.js)
- Автообновление: графики — раз в минуту, таблица и summary — раз в секунду, полная синхронизация с Google Drive — раз в 5 минут
- Автозапуск сервиса при перезагрузке сервера (systemd)

## Структура проекта
```
LogerAPI/
├── app/
│   ├── api.py           # FastAPI endpoints
│   ├── constants.py     # Константы
│   ├── gdrive_logger.py # Работа с Google Drive
│   └── static/          # index.html, style.css, script.js
├── main.py              # Точка входа FastAPI
├── requirements.txt     # Зависимости
├── setup_logger_api.sh  # Скрипт для автозапуска и открытия порта
├── remove_logger_api_autostart.sh # Скрипт для удаления автозапуска
├── test_api_request.py  # Пример тестового запроса к API
```

## Быстрый старт (Ubuntu)
1. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Создайте OAuth2-клиент Google API** и положите `client_secret.json` в корень проекта. При первом запуске потребуется пройти авторизацию в браузере.
3. **Откройте порт и настройте автозапуск:**
   ```bash
   bash setup_logger_api.sh
   ```
   После запуска скрипт выведет ссылку для доступа к API и UI.
4. **Откройте интерфейс:**
   Перейдите по ссылке, которую покажет скрипт, например:
   http://<ip_сервера>:7998/

## Отключить автозапуск
```bash
bash remove_logger_api_autostart.sh
```

## API
### POST `/log`
Пример тела запроса (JSON):
```json
{
  "filename": "example.mp3",
  "duration": 123.4,
  "size": 1048576,
  "received_at": "2025-07-21 12:34:56",
  "queue_time": 2.1,
  "process_time": 1.7,
  "text": "Распознанный текст"
}
```

### GET `/stats`
Возвращает статистику по времени поступления файлов (для графика).

### GET `/histogram`
Гистограмма по дням (для второго графика).

### GET `/logs?filename=&date=`
Список логов с фильтрами по имени и дате. Каждый лог содержит уникальный `file_id` для удаления.

### GET `/log_text?filename=...&received_at=...`
Текст конкретного лога.

### GET `/summary`
Общее количество файлов и суммарное время.

### DELETE `/log?file_id=...`
Удаляет лог по уникальному идентификатору Google Drive (`file_id`).

## UI
- Тёмный современный дизайн
- Два графика (по минутам и по дням)
- Фильтры по имени и дате
- Таблица логов с кнопками "Открыть" и "Удалить" (удаление по id, без подтверждения)
- Графики обновляются раз в минуту, таблица и summary — раз в секунду, полная синхронизация с Google Drive — раз в 5 минут

## Тестирование API
Пример тестового скрипта: `test_api_request.py`
```python
import urllib.request
import json

url = "http://localhost:7998/log"
data = {
    "filename": "testfile.txt",
    "duration": 42.5,
    "size": 12345,
    "received_at": "2025-07-21 12:34:56",
    "queue_time": 1.2,
    "process_time": 0.8,
    "text": "Тестовый лог"
}
headers = {"Content-Type": "application/json"}

try:
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers)
    with urllib.request.urlopen(req) as resp:
        print("Status:", resp.status)
        print("Response:", resp.read().decode())
except Exception as e:
    print("Ошибка запроса:", e)
```