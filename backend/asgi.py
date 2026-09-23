import os
import sys

# Ensure backend directory is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Set globalization for Spire on Linux
os.environ.setdefault("DOTNET_SYSTEM_GLOBALIZATION_INVARIANT", "1")

from a2wsgi import WSGIMiddleware
from mcp_server import mcp
from app import app as flask_app

# Disable strict DNS rebinding checks so Render's *.onrender.com host headers work smoothly
try:
    from mcp.server.transport_security import TransportSecuritySettings
    sec = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    app = mcp.sse_app(transport_security=sec)
except Exception:
    app = mcp.sse_app()

# Mount the Flask WSGI app at the root.
# MCP SSE (/sse and /messages) takes precedence; all other paths (/, /api/*, /static/*)
# fall through to Flask to serve the React web UI and REST API.
app.mount("/", WSGIMiddleware(flask_app))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting unified PESU Scrape & MCP server on http://{host}:{port}")
    print(f" - Web UI:  http://{host}:{port}/")
    print(f" - MCP SSE: http://{host}:{port}/sse")
    uvicorn.run(app, host=host, port=port)
