# EnCore's SnapSave — Backend

FastAPI media extraction and download streaming server with `pytubefix` and `yt-dlp`.

## Setup Steps

```bash
# 1. Create a Python virtual environment
python -m venv venv

# 2. Activate the virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# Linux/macOS:
source venv/bin/activate

# 3. Install required packages
pip install -r requirements.txt

# 4. Start the server
python app.py
```

The server runs on `http://localhost:8000`.  
Interactive API docs are available at `http://localhost:8000/docs`.
