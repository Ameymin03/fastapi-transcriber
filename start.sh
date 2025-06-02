#!/bin/bash

# Start the FastAPI backend in the background
uvicorn backend:app --host 0.0.0.0 --port 8001 &

# Optional delay to ensure backend is ready
sleep 2

# Start the Flask frontend using Gunicorn
gunicorn frontend:app --bind 0.0.0.0:10000
