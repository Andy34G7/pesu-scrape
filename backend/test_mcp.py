import asyncio
import os
import sys
import tempfile
import json

os.environ.setdefault("DOTNET_SYSTEM_GLOBALIZATION_INVARIANT", "1")
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from mcp_server import mcp


def extract_tool_result(res):
    if hasattr(res, "structured_content") and res.structured_content and "result" in res.structured_content:
        return res.structured_content["result"]
    if hasattr(res, "content") and res.content:
        if len(res.content) == 1:
            return json.loads(res.content[0].text)
        return [json.loads(c.text) for c in res.content]
    return None


async def test_mcp_server():
    print("Testing MCP Server Tool Registry and Execution...")

    # 1. Verify list_tools
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]
    print(f"[PASS] Discovered {len(tools)} tools: {tool_names}")
    
    expected_tools = [
        "pesu_login",
        "pesu_status",
        "pesu_get_courses",
        "pesu_search_courses",
        "pesu_get_units",
        "pesu_get_classes",
        "pesu_download_class",
        "pesu_download_unit",
    ]
    for expected in expected_tools:
        assert expected in tool_names, f"Expected tool '{expected}' missing from MCP registry!"

    # 2. Test pesu_status
    status_res = await mcp.call_tool("pesu_status", {})
    status_data = extract_tool_result(status_res)
    print(f"[PASS] pesu_status result: {status_data}")

    # 3. Test pesu_login
    login_res = await mcp.call_tool("pesu_login", {})
    login_data = extract_tool_result(login_res)
    print(f"[PASS] pesu_login result: {login_data}")
    assert login_data.get("authenticated") is True, f"Login failed: {login_data}"

    # 4. Test pesu_get_courses
    courses_res = await mcp.call_tool("pesu_get_courses", {})
    courses = extract_tool_result(courses_res)
    assert isinstance(courses, list) and len(courses) > 0, "pesu_get_courses returned 0 courses"
    print(f"[PASS] pesu_get_courses -> total {len(courses)} courses available")

    # 5. Test pesu_search_courses
    search_res = await mcp.call_tool("pesu_search_courses", {"query": "Data"})
    matches = extract_tool_result(search_res)
    assert isinstance(matches, list) and len(matches) > 0, "pesu_search_courses returned 0 results for 'Data'"
    print(f"[PASS] pesu_search_courses('Data') -> found {len(matches)} match(es), first: {matches[0]['subjectName']} (ID: {matches[0]['id']})")

    print("\nALL MCP SERVER TESTS PASSED PERFECTLY!")


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
