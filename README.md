# PDF Unlocker API

Flask API to remove password protection from PDF files. Used by the [Profile](https://github.com/apurvchandel/Profile) website tool.

## Deploy on Render

1. Push this repo to GitHub.
2. In [Render](https://render.com): **New** → **Web Service**, connect this repo.
3. **Build command:** `pip install -r requirements.txt`
4. **Start command:** `gunicorn -b 0.0.0.0:$PORT app:app`
5. Deploy. Copy the service URL and set it in the Profile website's PDF Unlocker frontend (`unlock-pdf.html` → `API_URL`).

## API

- **GET /** – Health check
- **POST /unlock** – Form: `file` (PDF), `password` (optional). Returns unlocked PDF.

## Local run

```bash
pip install -r requirements.txt
python app.py
```

Runs at `http://localhost:10000`.
