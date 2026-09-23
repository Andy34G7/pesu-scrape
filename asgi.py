import os
import sys

repo_root = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(repo_root, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from asgi import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
