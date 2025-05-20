from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import re
import os
from typing import Optional

# Initialize FastAPI with metadata
app = FastAPI(
    title="YouTube Transcript API",
    description="API for fetching and storing YouTube video transcripts",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None
)

# Configure CORS middleware
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
    """Extract YouTube video ID from various URL formats with robust pattern matching"""
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

@app.get("/")
@app.head("/")  # Explicit handler for Render health checks
async def health_check():
    """Health check endpoint that responds to both GET and HEAD requests"""
    return Response(content=None, media_type="application/json")

@app.get("/process", tags=["Transcripts"])
async def process_video(
    video_url: str = Query(..., description="YouTube video URL"),
    language: str = Query("en", description="Language code for transcript (e.g., 'en', 'es')")
):
    """
    Fetch and store YouTube video transcript
    - Supports multiple YouTube URL formats
    - Handles multiple languages
    - Implements basic caching
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL. Supported formats:\n"
                   "- https://www.youtube.com/watch?v=VIDEO_ID\n"
                   "- https://youtu.be/VIDEO_ID\n"
                   "- https://www.youtube.com/embed/VIDEO_ID"
        )

    try:
        # Check cache first
        if cached := transcript_store.get(video_id):
            return cached

        # Fetch fresh transcript
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id,
            languages=[language] if language != "all" else None
        )
        
        # Process transcript
        text = " ".join([item['text'] for item in transcript])
        
        # Manage cache size
        if len(transcript_store) >= MAX_STORE_SIZE:
            transcript_store.pop(next(iter(transcript_store)))

        # Store results
        data = {
            "video_id": video_id,
            "video_url": video_url,
            "transcript": text,
            "language": language,
            "timestamp": datetime.now().isoformat(),
            "word_count": len(text.split()),
            "status": "success"
        }
        
        transcript_store[video_id] = data
        return data

    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Transcript unavailable: {str(e)}. "
                   "Possible reasons:\n"
                   "- Subtitles disabled for this video\n"
                   "- Invalid language code\n"
                   "- Video doesn't exist"
        )

@app.get("/transcripts", tags=["Transcripts"])
async def get_all_transcripts(
    limit: int = Query(10, ge=1, le=50, description="Number of transcripts to return (1-50)"),
    offset: int = Query(0, ge=0, description="Number of transcripts to skip")
):
    """Get paginated list of stored transcripts with metadata"""
    transcripts = list(transcript_store.values())
    return {
        "count": len(transcripts),
        "limit": limit,
        "offset": offset,
        "results": transcripts[offset:offset+limit]
    }

@app.get("/transcripts/{video_id}", tags=["Transcripts"])
async def get_transcript(video_id: str):
    """Get specific transcript by video ID with full metadata"""
    if video_id not in transcript_store:
        raise HTTPException(
            status_code=404,
            detail=f"No transcript found for video ID: {video_id}"
        )
    return transcript_store[video_id]

# Production-ready server configuration
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        timeout_keep_alive=60,
        access_log=True
    )
