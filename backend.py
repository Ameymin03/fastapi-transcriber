from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
from datetime import datetime
import re
import os
import uvicorn  # Explicit import for running the server
from typing import Optional

app = FastAPI(
    title="YouTube Transcript API",
    version="1.0.0",
    docs_url="/docs"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store with maximum size
transcript_store = {}
MAX_STORE_SIZE = 100

def extract_video_id(url: str) -> Optional[str]:
    """Improved URL parsing with regex"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'embed\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        if match := re.search(pattern, url):
            return match.group(1)
    return None

@app.get("/")
@app.head("/")
async def health_check():
    """Essential health check endpoint"""
    return Response(status_code=200)

@app.get("/process")
async def process_video(
    video_url: str = Query(...),
    language: str = Query("en")
):
    video_id = extract_video_id(video_url)
    if not video_id:
        raise HTTPException(400, detail="Invalid YouTube URL")
    
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
        text = " ".join([item['text'] for item in transcript])
        
        # Manage cache size
        if len(transcript_store) >= MAX_STORE_SIZE:
            transcript_store.pop(next(iter(transcript_store)))
            
        data = {
            "video_id": video_id,
            "transcript": text,
            "timestamp": datetime.now().isoformat()
        }
        transcript_store[video_id] = data
        return data
    except Exception as e:
        raise HTTPException(400, detail=str(e))

def run_server():
    """Explicit server configuration for Render"""
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        timeout_keep_alive=60,
        access_log=True
    )

if __name__ == "__main__":
    run_server()
