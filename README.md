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

## MCP Server (Model Context Protocol)

This repository includes a built-in MCP server that enables AI assistants (Claude Desktop, Antigravity, Cursor, Cline, etc.) to query course information and fetch lecture materials.

### Exposed Tools
- `pesu_login`: Authenticate with student credentials (reads `PESU_USERNAME` and `PESU_PASSWORD` from `.env` by default).
- `pesu_status`: Check authentication state.
- `pesu_get_courses`: List enrolled courses across semesters.
- `pesu_search_courses`: Search courses by course name or code.
- `pesu_get_units`: List syllabus units for a course.
- `pesu_get_classes`: List classes/lectures with slide, note, and MCQ availability indicators.
- `pesu_get_mcqs`: Fetch structured Multiple Choice Questions (MCQs) and answer keys for a specific class.
- `pesu_get_unit_mcqs`: Fetch all MCQs across all classes in an entire syllabus unit.
- `pesu_download_class`: Download slides or notes for a single class (with automatic PDF conversion).
- `pesu_download_unit`: Download and optionally merge all slides or notes for a unit into a consolidated PDF.

### Running the MCP Server
```bash
./backend/venv/bin/python mcp_server.py
```

### Testing the MCP Server
```bash
./backend/venv/bin/python backend/test_mcp.py
```

### Client Configuration (`mcp_config.json` / Claude Desktop / Cursor)
```json
{
  "mcpServers": {
    "pesu-academy": {
      "command": "/path/to/pesu-scrape/backend/venv/bin/python",
      "args": ["/path/to/pesu-scrape/mcp_server.py"],
      "env": {
        "DOTNET_SYSTEM_GLOBALIZATION_INVARIANT": "1"
      }
    }
  }
}
```

## Note
This project is mostly vibecoded. Code has been rewritten to change/fix things.

