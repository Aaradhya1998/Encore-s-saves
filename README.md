# EnCore's SnapSave

> Universal high-speed media video & audio downloader web application.  
> Supports **YouTube**, **YouTube Shorts**, **Instagram**, **Instagram Reels**, **TikTok**, **X (Twitter)**, **Facebook**, and more.  
> Designed with the minimalist editorial design system matching **DoYour To-Do** for **EnCore's 20 Projects 2026**.

---

## Features

- **Hybrid Extraction Engine**:
  - Primary for YouTube & Shorts: `pytubefix` (handles progressive MP4, adaptive high-res video, and pure audio streams).
  - Multi-platform & fallback: `yt-dlp` (Instagram, Reels, TikTok, X/Twitter, Facebook, etc.).
- **Automatic Platform Detection**: Detects links from YouTube, Shorts, Instagram, Reels, TikTok, X, and Facebook.
- **Rich Media Preview**: Shows high-resolution thumbnail, duration badge, title, uploader/channel name, and extraction engine.
- **Quality & Format Selection**:
  - Video: 1080p Full HD, 720p HD, 480p, 360p (with file size estimation).
  - Audio: High-Quality MP3 (192kbps) and original AAC M4A.
- **Fast In-Browser Downloads**: Directly streams binary attachments to browser with automatic filename formatting.
- **Safe Auto-Cleanup**: Temporary media files in `backend/downloads/` are auto-purged immediately upon download delivery and garbage-collected if older than 10 minutes.
- **Built-in Rate Limiting**: In-memory sliding window rate limiter protects server from overload.
- **Passwordless Supabase Auth**: Optional passwordless magic link sign-in matching DoYour To-Do, with instant guest bypass for development.

---

## Folder Structure

```
Encore's saves/
├── backend/
│   ├── app.py              # FastAPI server (CORS, streaming, rate limits)
│   ├── downloader.py       # pytubefix + yt-dlp download engine
│   ├── requirements.txt    # Python dependencies
│   ├── README.md           # Backend setup guide
│   └── downloads/          # Temporary files (auto-cleaned)
├── frontend/
│   ├── index.html          # Main video downloader interface
│   ├── login.html          # Passwordless sign-in page (DoYour To-Do style)
│   ├── css/style.css       # Monochrome editorial design system
│   ├── js/script.js        # Main UI controller & stream selector
│   ├── js/api.js           # Fetch API client (health, info, download)
│   ├── js/supabase-client.js # Auth client with fallback
│   └── logo/
│       ├── logo.png        # App logo
│       └── logo.svg        # Scalable vector logo
└── README.md               # Project documentation
```

---

## Quick Start (Running Backend & Frontend Together)

### 1. Backend Setup & Run

Open PowerShell or Terminal in the `backend/` folder:

```bash
cd backend

# Create virtual environment (optional but recommended)
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
python app.py
# Or with uvicorn directly:
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

The backend server starts on: **`http://localhost:8000`**

### 2. Frontend Access

The FastAPI backend automatically mounts the `frontend/` directory. You can open:

- **Main Downloader**: [http://localhost:8000/](http://localhost:8000/) or [http://localhost:8000/index.html](http://localhost:8000/index.html)
- **Login Page**: [http://localhost:8000/login.html](http://localhost:8000/login.html)
- **API Health**: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

*Note:* You can also open `frontend/index.html` directly in any web browser or via VS Code Live Server — CORS is enabled on the backend to allow requests from any local frontend.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check & auto-purges stale temporary downloads |
| `POST` | `/api/info` | Accepts `{"url": "..."}`, returns title, thumbnail, duration, uploader, platform, and available formats |
| `POST` | `/api/download` | Accepts `{"url": "...", "format_id": "...", "ext": "mp4"}`, downloads and streams media file to client |

---

## Legal & Compliance Notice

For personal use only. Respect copyright laws, intellectual property rights, and each platform's Terms of Service.

---

© 2026 – Made by Aaradhya For {EnCore's 20 Projects 2026}
