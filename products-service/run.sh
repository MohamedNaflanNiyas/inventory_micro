#!/bin/sh

echo "---Booting up background consumer worker..."
# Start worker in background and redirect output stream directly to the main terminal window
python -u app/worker.py &

echo "---Starting FastAPI Application Instance..."
# Explicitly matching port 5002
uvicorn app.main:app --host 0.0.0.0 --port 5002 