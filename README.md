# work-agent-backend

FastAPI backend для VDI AI Control Center. На этом этапе — mock runtime без реальных
OBS/ESP32/OCR/LLM, но с полноценным API и WebSocket.

## Запуск

```powershell
cd work-agent-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs  
WebSocket: ws://localhost:8000/ws/events

## Архитектура

```
app/
  main.py              — точка входа FastAPI
  api/                 — HTTP-роуты
  core/
    config.py          — настройки
    event_bus.py       — pub/sub событий
    websocket_manager.py
  models/              — Pydantic-схемы
  services/            — бизнес-логика и mock runtime
  storage/             — in-memory репозитории
  mocks/initial_data.py — сид
```
