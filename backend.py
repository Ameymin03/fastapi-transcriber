from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
from datetime import datetime
import re
from typing import Optional

app = FastAPI(
    title="YouTube Transcript API",
    description="API for fetching YouTube video transcripts",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only - restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

transcript_cache = {}
MAX_CACHE_SIZE = 100

def extract_video_id(url: str) -> Optional[str]:
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
    return Response(status_code=200)

@app.get("/process")
async def process_video(
    video_url: str = Query(...),
    language: str = Query("en")
):
    video_id = extract_video_id(video_url)
    if not video_id:
        raise HTTPException(400, detail="Invalid YouTube URL format")

    try:
        if cached := transcript_cache.get(video_id):
            return cached

        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
        text = " ".join([item['text'] for item in transcript])
        
        if len(transcript_cache) >= MAX_CACHE_SIZE:
            transcript_cache.pop(next(iter(transcript_cache)))

        result = {
            "video_id": video_id,
            "transcript": text,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
        transcript_cache[video_id] = result
        return result

    except Exception as e:
        raise HTTPException(404, detail=f"Transcript unavailable: {str(e)}")

# Remove the if __name__ == "__main__" block completely
# Render will use the uvicorn command directly from render.yaml
