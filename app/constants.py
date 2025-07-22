# constants.py
GOOGLE_CREDENTIALS_FILE = 'client_secret.json'
GOOGLE_TOKEN_FILE = 'token.json'
GOOGLE_DRIVE_FOLDER_NAME = 'LogerAPI_Logs'
DATE_FORMAT = '%Y-%m-%d'
LOG_FILE_EXTENSION = '.txt'
UI_UPDATE_INTERVAL_MS = 1000

# --- UI/JS constants ---
UI_CONST = {
    'UPDATE_INTERVAL_MS': 60000,  # 1 минута
    'NO_DATA_TEXT': 'Нет данных',
    'DELETE_CONFIRM_TEXT': 'Удалить лог?',
    'DELETE_ERROR_TEXT': 'Ошибка удаления',
    'TOTAL_FILES_LABEL': 'Всего файлов',
    'TOTAL_DURATION_LABEL': 'Общее время',
    'DURATION_SEC': 'сек',
    'DURATION_MIN': 'мин',
    'DURATION_HOUR': 'ч',
    'OPEN_BTN_LABEL': 'Открыть',
    'DELETE_BTN_LABEL': 'Удалить',
    'CHART_LABEL_MINUTES': 'Количество файлов (по минутам)',
    'CHART_LABEL_DAYS': 'Файлов за день',
    'CHART_X_MINUTES': 'Время (минуты)',
    'CHART_X_DAYS': 'Дата',
    'CHART_Y_FILES': 'Файлов',
}
