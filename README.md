# PESU Scrape

# PESU Scrape

A full-stack application to scrape and view PESU course details, slides, and notes.

## Tech Stack

- **Frontend**: React, Vite, TailwindCSS
- **Backend**: Python, Flask, Gunicorn
- **Database**: SQLite (or similar, managed by backend)
- **Deployment**: Docker

## Getting Started

### Local Development

1. **Backend**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python3 app.py
   # Runs on http://localhost:5000
   ```

2. **Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   # Runs on http://localhost:5173 (proxies API to 5000)
   ```

## Docker Deployment (Recommended)

This project is containerized to serve both frontend and backend from a single image.

### Build and Run
```bash
docker build -t pesu-scrape .
docker run -p 5000:5000 pesu-scrape
```
Visit http://localhost:5000.

## Note
This project is mostly vibecoded. Code has been rewritten to change/fix things.
