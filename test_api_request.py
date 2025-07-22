import urllib.request
import json
import random
import time

url = "http://localhost:7998/log"
headers = {"Content-Type": "application/json"}

for i in range(15):
    data = {
        "filename": f"testfile_{i+1}.txt",
        "duration": round(random.uniform(10, 300), 2),
        "size": random.randint(1000, 10_000_000),
        "received_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + i)),
        "queue_time": round(random.uniform(0.5, 5.0), 2),
        "process_time": round(random.uniform(0.2, 2.0), 2),
        "text": f"Тестовый лог номер {i+1} — случайное значение: {random.randint(1000,9999)}"
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers)
        with urllib.request.urlopen(req) as resp:
            print(f"Запрос {i+1}: Status:", resp.status)
            print("Response:", resp.read().decode())
    except Exception as e:
        print(f"Ошибка запроса {i+1}:", e)
    time.sleep(0.2)  # небольшая пауза между запросами
