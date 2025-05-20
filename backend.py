from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import re
import os
from typing import Optional

app = FastAPI(
    title="YouTube Transcript API",
    description="API for fetching and storing YouTube video transcripts",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://flask-transcriber-ui.onrender.com",
        "http://localhost:3000"  # For local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory transcript storage with size limit
transcript_store = {}
MAX_STORE_SIZE = 100  # Prevent memory overload

def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'embed\/([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@app.get("/", tags=["Health Check"])
async def root():
    """Health check endpoint"""
    return {
        "status": "active",
        "service": "YouTube Transcript API",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/process", tags=["Transcripts"])
async def process_video(
    video_url: str = Query(..., description="YouTube video URL"),
    language: str = Query("en", description="Language code for transcript")
):
    """Fetch and store YouTube video transcript"""
    video_id = extract_video_id(video_url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL. Supported formats: "
                   "youtube.com/watch?v=ID, youtu.be/ID, youtube.com/embed/ID"
        )

    try:
        # Check cache first
        if video_id in transcript_store:
            return transcript_store[video_id]

        # Fetch transcript
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id,
            languages=[language] if language != "all" else None
        )
        
        text = " ".join([item['text'] for item in transcript])
        
        # Store data (with cache eviction if needed)
        if len(transcript_store) >= MAX_STORE_SIZE:
            oldest_key = next(iter(transcript_store))
            transcript_store.pop(oldest_key)

        data = {
            "video_id": video_id,
            "video_url": video_url,
            "transcript": text,
            "language": language,
            "timestamp": datetime.now().isoformat(),
            "word_count": len(text.split())
        }
        
        transcript_store[video_id] = data
        return data

    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Transcript not available: {str(e)}"
        )

@app.get("/transcripts", tags=["Transcripts"])
async def get_all_transcripts(
    limit: int = Query(10, description="Number of transcripts to return"),
    skip: int = Query(0, description="Number of transcripts to skip")
):
    """Get paginated list of stored transcripts"""
    transcripts = list(transcript_store.values())
    return {
        "count": len(transcripts),
        "transcripts": transcripts[skip:skip+limit]
    }

@app.get("/transcripts/{video_id}", tags=["Transcripts"])
async def get_transcript(video_id: str):
    """Get specific transcript by video ID"""
    if video_id not in transcript_store:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript_store[video_id]

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
