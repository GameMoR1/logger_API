import urllib.request
import json

url = "http://localhost:7998/log"
data = {
    "filename": "testfile.txt",
    "duration": 41.5,
    "size": 1345,
    "received_at": "2025-07-21 12:36:56",
    "queue_time": 1.2,
    "process_time": 0.8,
    "text": "Тестовый лог ляляля"
}
headers = {"Content-Type": "application/json"}

try:
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers)
    with urllib.request.urlopen(req) as resp:
        print("Status:", resp.status)
        print("Response:", resp.read().decode())
except Exception as e:
    print("Ошибка запроса:", e)
