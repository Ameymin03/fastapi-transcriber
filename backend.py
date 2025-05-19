from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import re

#creating fastapi
app = FastAPI()

#Allowing Cross-Origin Requests
# Adds middleware to allow requests from any domain (*)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#in-memory transcript storage
transcript_store = {}

#function to extract yt-video ID
def extract_video_id(url: str):
    parsed_url = urlparse(url)
    if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        if parsed_url.path == '/watch':
            query_params = parse_qs(parsed_url.query)
            return query_params.get('v', [None])[0]
        #If URL is in the format youtube.com/watch?v=abc123, it extracts the v query parameter.
        elif parsed_url.path.startswith('/embed/'):
            return parsed_url.path.split('/embed/')[1]
    elif parsed_url.hostname == 'youtu.be':
        return parsed_url.path.lstrip('/')
    return None

# def summarize_text(text: str) -> str:
#     sentences = re.split(r'(?<=[.!?]) +', text)
#     summary = ' '.join(sentences[:3])
#     return summary if summary else text[:200] + "..."

#Base route to check if the API is running.
@app.get("/")
async def root():
    return {"message": "YouTube Transcript API is running."}

#Main route to process yt video
@app.get("/process")
async def process_video(video_url: str):
    video_id = extract_video_id(video_url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid or unsupported YouTube URL format.")
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([item['text'] for item in transcript])
        #summary = summarize_text(text)
        data = {
            "video_id": video_id,
            "video_url": video_url,
            "transcript": text,
            #"summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        transcript_store[video_id] = data
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Transcript not available for this youtube video")

@app.get("/all_transcripts")
async def get_all_transcripts(): 
    return list(transcript_store.values())


