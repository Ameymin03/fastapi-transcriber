#!/bin/bash

# Start the FastAPI backend using uvicorn in the background
uvicorn backend:app --host 0.0.0.0 --port 8001 &

# Give backend a second or two to start
sleep 2

# Start the Flask frontend in the foreground (so Render keeps the service alive)
python frontend.py
