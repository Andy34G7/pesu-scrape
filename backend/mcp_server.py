import os
import sys
import tempfile
import re
import logging
from typing import Optional, List, Dict, Any

# Ensure proper globalization for Spire library on Linux
os.environ.setdefault("DOTNET_SYSTEM_GLOBALIZATION_INVARIANT", "1")

# Configure logger to write strictly to stderr
logger = logging.getLogger("pesu_mcp_server")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Ensure backend directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Load environment variables (.env)
try:
    from dotenv import load_dotenv
    for p in [os.getcwd(), current_dir, os.path.dirname(current_dir)]:
        env_file = os.path.join(p, ".env")
        if os.path.isfile(env_file):
            load_dotenv(env_file)
            break
except ImportError:
    pass

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer

from pesu_client import PESUClient
from pdf_utils import convert_to_pdf, merge_pdfs

# Initialize MCP server
mcp = MCPServer("pesu-academy")

# Persistent PESU client instance for the server session
_client = PESUClient()
_active_user = None


def _ensure_authenticated(username: Optional[str] = None, password: Optional[str] = None) -> tuple[bool, str]:
    global _active_user
    
    # If already authenticated and session is alive, reuse it
    if _client.is_authenticated and not username:
        if _client.is_session_alive():
            return True, f"Already authenticated as {_active_user}"
        else:
            logger.info("Session expired. Refreshing authentication...")

    user = username or os.environ.get("PESU_USERNAME")
    pwd = password or os.environ.get("PESU_PASSWORD")

    if not user or not pwd:
        return False, "Missing credentials. Provide username/password or set PESU_USERNAME and PESU_PASSWORD in .env."

    success, msg = _client.authenticate(user, pwd)
    if success:
        _active_user = user
        return True, f"Successfully authenticated as {user}"
    return False, f"Authentication failed: {msg}"


@mcp.tool()
def pesu_login(username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
    """
    Authenticate with PESU Academy using student PRN/SRN and password.
    If username and password are not provided, they are read from PESU_USERNAME and PESU_PASSWORD
    in the environment or .env file.
    """
    success, msg = _ensure_authenticated(username, password)
    return {
        "success": success,
        "message": msg,
        "authenticated": _client.is_authenticated,
        "username": _active_user
    }


@mcp.tool()
def pesu_status() -> Dict[str, Any]:
    """
    Check the current PESU Academy authentication status and active session user.
    """
    return {
        "authenticated": _client.is_authenticated,
        "username": _active_user,
        "has_credentials_in_env": bool(os.environ.get("PESU_USERNAME") and os.environ.get("PESU_PASSWORD"))
    }


@mcp.tool()
def pesu_get_courses(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    List all courses the student is enrolled in across all semesters.
    Auto-authenticates using environment credentials if not already logged in.
    Returns a list of course dictionaries with 'id', 'subjectCode', 'subjectName', and 'semester'.
    """
    auth_ok, auth_msg = _ensure_authenticated()
    if not auth_ok:
        raise RuntimeError(auth_msg)

    courses = _client.get_subjects(force_refresh=force_refresh)
    return courses


@mcp.tool()
def pesu_search_courses(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Search through the student's enrolled courses matching a query keyword
    in the course code or name (case-insensitive, e.g. 'Software Engineering', 'CS341', 'Data', 'Machine Learning').
    """
    auth_ok, auth_msg = _ensure_authenticated()
    if not auth_ok:
        raise RuntimeError(auth_msg)

    courses = _client.get_subjects()
    q = query.strip().lower()
    matches = [
        c for c in courses
        if q in c.get("subjectName", "").lower() or q in c.get("subjectCode", "").lower() or q == str(c.get("id", "")).strip()
    ]
    return matches[:limit]


@mcp.tool()
def pesu_get_units(course_id: str) -> List[Dict[str, Any]]:
    """
    List syllabus units/modules for a given course ID (e.g. '22902').
    Returns a list of unit dictionaries with 'unitId', 'title', and 'description'.
    """
    auth_ok, auth_msg = _ensure_authenticated()
    if not auth_ok:
        raise RuntimeError(auth_msg)

    units = _client.get_units(course_id)
    return units


@mcp.tool()
def pesu_get_classes(unit_id: str) -> List[Dict[str, Any]]:
    """
    List all classes / topics in a unit (e.g. '69624').
    Returns a list of class objects containing:
      - 'classId': unique ID for downloading slides/notes
      - 'title': topic/class name
      - 'hasSlides': boolean indicating whether slide decks are uploaded
      - 'hasNotes': boolean indicating whether notes documents are uploaded
      - 'slidesCount': number of slide files uploaded
      - 'notesCount': number of note files uploaded
    """
    auth_ok, auth_msg = _ensure_authenticated()
    if not auth_ok:
        raise RuntimeError(auth_msg)

    classes = _client.get_classes(unit_id)
    return classes


@mcp.tool()
def pesu_download_class(
    course_id: str,
    class_id: str,
    resource_type: str = "slides",
    output_dir: Optional[str] = None,
    convert_pdf: bool = True
) -> Dict[str, Any]:
    """
    Download materials for a single class (slides or notes).
    Args:
      - course_id: Course ID (e.g. '22902')
      - class_id: Class ID (e.g. '3f0ce449-ec4d-449a-a113-f9233218bbb5')
      - resource_type: 'slides' (or '2') for presentation slides, 'notes' (or '3') for notes/documents
      - output_dir: Optional directory to store downloads. Defaults to ~/Downloads/pesu_materials.
      - convert_pdf: Convert PPTX/DOCX/image files to PDF automatically (default: True).
    Returns:
      Dict with 'success', 'files' (list of absolute file paths), and 'message'.
    """
    auth_ok, auth_msg = _ensure_authenticated()
    if not auth_ok:
        raise RuntimeError(auth_msg)

    rt = "3" if str(resource_type).strip().lower() in ["3", "notes", "note"] else "2"
    rt_name = "notes" if rt == "3" else "slides"

    target_dir = output_dir or os.path.expanduser("~/Downloads/pesu_materials")
    os.makedirs(target_dir, exist_ok=True)

    raw_path = os.path.join(target_dir, f"{class_id}_{rt_name}_raw")
    success, downloaded_paths = _client.download_file(course_id, class_id, raw_path, resource_type=rt)

    if not success or not downloaded_paths:
        return {
            "success": False,
            "files": [],
            "message": f"No {rt_name} found or failed to download for class {class_id} in course {course_id}."
        }

    final_files = []
    for path in downloaded_paths:
        if convert_pdf and not path.lower().endswith(".pdf"):
            pdf_path = os.path.splitext(path)[0] + ".pdf"
            if convert_to_pdf(path, pdf_path):
                final_files.append(os.path.abspath(pdf_path))
                continue
        final_files.append(os.path.abspath(path))

    return {
        "success": True,
        "files": final_files,
        "message": f"Successfully downloaded {len(final_files)} {rt_name} file(s)."
    }


@mcp.tool()
def pesu_download_unit(
    course_id: str,
    unit_id: str,
    resource_type: str = "slides",
    merge_pdf: bool = True,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Download all available materials in an entire unit and optionally merge them into
    a single consolidated PDF (e.g. Unit 1 Slides Book).
    Args:
      - course_id: Course ID (e.g. '22902')
      - unit_id: Unit ID (e.g. '69624')
      - resource_type: 'slides' (or '2') for slides, 'notes' (or '3') for notes
      - merge_pdf: When True, merges all converted PDFs into one unified PDF (default: True).
      - output_dir: Optional destination directory (defaults to ~/Downloads/pesu_materials).
    Returns:
      Dict with 'success', 'output_path' or 'files', and summary 'message'.
    """
    auth_ok, auth_msg = _ensure_authenticated()
    if not auth_ok:
        raise RuntimeError(auth_msg)

    rt = "3" if str(resource_type).strip().lower() in ["3", "notes", "note"] else "2"
    rt_name = "notes" if rt == "3" else "slides"

    classes = _client.get_classes(unit_id)
    if not classes:
        return {"success": False, "message": f"No classes found for unit {unit_id}."}

    eligible = [
        cls for cls in classes
        if (cls.get("hasNotes") if rt == "3" else cls.get("hasSlides"))
    ]

    if not eligible:
        return {
            "success": False,
            "message": f"No {rt_name} uploaded for any classes in unit {unit_id}."
        }

    target_dir = output_dir or os.path.expanduser("~/Downloads/pesu_materials")
    os.makedirs(target_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        collected_pdfs = []
        downloaded_count = 0

        for cls in eligible:
            cid = cls["classId"]
            title = cls.get("title", cid)
            safe_title = re.sub(r'[^\w\-.]', '_', title)
            raw_output = os.path.join(temp_dir, f"{safe_title}_{cid}")
            ok, paths = _client.download_file(course_id, cid, raw_output, resource_type=rt)
            if ok and paths:
                downloaded_count += 1
                for p in paths:
                    pdf_target = os.path.splitext(p)[0] + ".pdf"
                    if convert_to_pdf(p, pdf_target):
                        collected_pdfs.append(pdf_target)
                    elif p.lower().endswith(".pdf"):
                        collected_pdfs.append(p)

        if not collected_pdfs:
            return {
                "success": False,
                "message": f"Failed to download or convert any {rt_name} files in unit {unit_id}."
            }

        if merge_pdf:
            merged_filename = f"course_{course_id}_unit_{unit_id}_{rt_name}_merged.pdf"
            final_merged_path = os.path.join(target_dir, merged_filename)
            merge_pdfs(collected_pdfs, final_merged_path)
            return {
                "success": True,
                "output_path": os.path.abspath(final_merged_path),
                "downloaded_classes": downloaded_count,
                "total_pdfs_merged": len(collected_pdfs),
                "message": f"Merged {len(collected_pdfs)} {rt_name} files into {os.path.abspath(final_merged_path)}"
            }
        else:
            copied_files = []
            for p in collected_pdfs:
                dest = os.path.join(target_dir, os.path.basename(p))
                import shutil
                shutil.copyfile(p, dest)
                copied_files.append(os.path.abspath(dest))
            return {
                "success": True,
                "files": copied_files,
                "downloaded_classes": downloaded_count,
                "message": f"Downloaded {len(copied_files)} {rt_name} files to {target_dir}"
            }


def main():
    if "--test" in sys.argv:
        sys.stderr.write("Testing PESU Academy MCP Server...\n")
        auth_ok, auth_msg = _ensure_authenticated()
        sys.stderr.write(f"Auth check: {auth_msg} (ok={auth_ok})\n")
        if auth_ok:
            courses = _client.get_subjects()
            sys.stderr.write(f"Retrieved {len(courses)} courses successfully.\n")
        sys.stderr.write("MCP Server initialized and ready for stdio transport.\n")
        return

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
