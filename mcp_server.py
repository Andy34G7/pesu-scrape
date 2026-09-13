#!/usr/bin/env python3
"""
PESU Academy MCP Server Runner
Allows AI assistants and agents (Claude, Cursor, Antigravity, Cline, etc.)
to query PESU Academy courses, units, classes, and materials.
"""
import os
import sys

# Add backend to sys.path
repo_root = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(repo_root, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from mcp_server import main

if __name__ == "__main__":
    main()
