"""
EnCore's SnapSave - FastAPI Backend Server
Provides media extraction, download streaming, rate limiting, and CORS.
"""

import os
import time
from collections import defaultdict
from typing import Dict, Any, Optional
from pydantic import BaseModel, HttpUrl
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from downloader import (
    get_media_info,
    download_media,
    cleanup_old_downloads,
    MediaExtractError,
    DOWNLOADS_DIR,
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Ensure downloads directory exists on startup
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# App instance
app = FastAPI(
    title="EnCore's SnapSave API",
    description="High-performance media extractor and downloader for YouTube, Instagram, and more.",
    version="1.0.0"
)

# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory Rate Limiting
# Max 30 requests per minute per client IP
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 30
request_history = defaultdict(list)


def check_rate_limit(client_ip: str):
    """Simple sliding window rate limiter."""
    now = time.time()
    history = request_history[client_ip]
    # Prune old timestamps
    request_history[client_ip] = [t for t in history if now - t < RATE_LIMIT_WINDOW]
    if len(request_history[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before sending more requests."
        )
    request_history[client_ip].append(now)


# Request schemas
class MediaInfoRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    format_id: str
    ext: Optional[str] = "mp4"


def safe_remove_file(file_path: str):
    """Background task to remove temporary file after response streaming."""
    try:
        # Give a short delay to ensure socket flush on some operating systems
        time.sleep(2)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Failed to remove file {file_path}: {e}")


@app.on_event("startup")
async def startup_event():
    """Startup hook: clean old temp files and prepare directory."""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    cleanup_old_downloads(max_age_seconds=600)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    cleaned = cleanup_old_downloads(max_age_seconds=600)
    return {
        "status": "ok",
        "app": "EnCore's SnapSave",
        "version": "1.0.0",
        "cleaned_files": cleaned
    }


@app.post("/api/info")
async def fetch_info(req: MediaInfoRequest, request: Request):
    """
    Fetch media information: title, thumbnail, duration, uploader,
    platform, and available formats.
    """
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty.")

    try:
        info = get_media_info(url)
        return info
    except MediaExtractError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while fetching video info: {str(e)}"
        )


@app.post("/api/download")
async def trigger_download(req: DownloadRequest, request: Request, background_tasks: BackgroundTasks):
    """
    Download requested media format and stream back as an attachment.
    Auto-deletes file once stream is completed.
    """
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty.")

    try:
        file_path, display_name, content_type = download_media(
            url=url,
            format_id=req.format_id,
            ext=req.ext or "mp4"
        )

        if not os.path.exists(file_path):
            raise HTTPException(status_code=500, detail="Downloaded file could not be found.")

        # Register auto-delete background task
        background_tasks.add_task(safe_remove_file, file_path)

        # Return file as direct browser attachment
        return FileResponse(
            path=file_path,
            filename=display_name,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{display_name}"',
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except MediaExtractError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Download execution failed: {str(e)}"
        )


# Mount frontend directory for full-stack serving convenience
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "frontend"))
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
