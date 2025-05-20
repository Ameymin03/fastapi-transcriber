from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
from datetime import datetime
import re
import os
import uvicorn
from typing import Optional

# Initialize FastAPI with production-ready settings
app = FastAPI(
    title="YouTube Transcript API",
    description="API for fetching YouTube video transcripts",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
    servers=[{"url": "https://your-render-service.onrender.com", "description": "Production server"}]
)

# Configure CORS for production and development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://flask-transcriber-ui.onrender.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache with size limit
transcript_cache = {}
MAX_CACHE_SIZE = 100  # Prevents memory overload

def extract_video_id(url: str) -> Optional[str]:
    """Robust YouTube video ID extraction from multiple URL formats"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})',  # Standard URLs
        r'youtu\.be\/([0-9A-Za-z_-]{11})',  # Short URLs
        r'embed\/([0-9A-Za-z_-]{11})'  # Embedded URLs
    ]
    for pattern in patterns:
        if match := re.search(pattern, url):
            return match.group(1)
    return None

@app.get("/")
@app.head("/")
async def health_check():
    """Render.com health check endpoint (must return 200 for HEAD requests)"""
    return Response(status_code=200)

@app.get("/process")
async def process_video(
    video_url: str = Query(..., description="YouTube video URL"),
    language: str = Query("en", description="Transcript language code")
):
    """
    Fetch and cache YouTube video transcript
    - Supports multiple URL formats
    - Handles 400+ error cases
    - Implements cache management
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube URL format. Supported examples:\n"
                   "• https://www.youtube.com/watch?v=VIDEO_ID\n"
                   "• https://youtu.be/VIDEO_ID\n"
                   "• https://www.youtube.com/embed/VIDEO_ID"
        )

    try:
        # Return cached result if available
        if video_id in transcript_cache:
            return transcript_cache[video_id]

        # Fetch fresh transcript
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id,
            languages=[language] if language != "all" else None
        )
        
        # Process transcript text
        text = " ".join([item['text'] for item in transcript])
        
        # Manage cache size
        if len(transcript_cache) >= MAX_CACHE_SIZE:
            transcript_cache.pop(next(iter(transcript_cache)))

        # Prepare response
        result = {
            "video_id": video_id,
            "transcript": text,
            "language": language,
            "timestamp": datetime.now().isoformat(),
            "word_count": len(text.split()),
            "status": "success"
        }
        
        transcript_cache[video_id] = result
        return result

    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Transcript unavailable. Possible reasons:\n"
                   f"- Subtitles disabled for this video\n"
                   f"- Invalid language code: {language}\n"
                   f"- Video doesn't exist\n"
                   f"Technical details: {str(e)}"
        )

@app.get("/transcripts")
async def list_transcripts(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0)
):
    """Paginated list of cached transcripts"""
    transcripts = list(transcript_cache.values())
    return {
        "count": len(transcripts),
        "limit": limit,
        "offset": offset,
        "results": transcripts[offset:offset+limit]
    }

def start_application():
    """Production-grade server configuration"""
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        access_log=True,
        timeout_keep_alive=60,
        workers=1
    )

if __name__ == "__main__":
    start_application()
