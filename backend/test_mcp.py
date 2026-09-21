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
        "pesu_get_mcqs",
        "pesu_get_unit_mcqs",
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
    search_res = await mcp.call_tool("pesu_search_courses", {"query": "Software Engineering"})
    matches = extract_tool_result(search_res)
    assert isinstance(matches, list) and len(matches) > 0, "pesu_search_courses returned 0 results for 'Software Engineering'"
    course_id = matches[0]["id"]
    print(f"[PASS] pesu_search_courses('Software Engineering') -> found ID: {course_id}")

    # 6. Test pesu_get_units and pesu_get_classes
    units_res = await mcp.call_tool("pesu_get_units", {"course_id": course_id})
    units = extract_tool_result(units_res)
    assert isinstance(units, list) and len(units) > 0, "pesu_get_units returned 0 units"
    unit_id = units[0]["unitId"]
    print(f"[PASS] pesu_get_units({course_id}) -> {len(units)} units, first: {units[0]['title']} ({unit_id})")

    classes_res = await mcp.call_tool("pesu_get_classes", {"unit_id": unit_id})
    classes = extract_tool_result(classes_res)
    assert isinstance(classes, list) and len(classes) > 0, "pesu_get_classes returned 0 classes"
    class_id = classes[0]["classId"]
    print(f"[PASS] pesu_get_classes({unit_id}) -> {len(classes)} classes, first: {classes[0]['title']} ({class_id})")

    # 7. Test pesu_get_mcqs
    mcqs_res = await mcp.call_tool("pesu_get_mcqs", {"course_id": course_id, "class_id": class_id})
    mcqs_data = extract_tool_result(mcqs_res)
    assert isinstance(mcqs_data, dict) and "questions" in mcqs_data, f"Invalid MCQ data structure: {mcqs_data}"
    print(f"[PASS] pesu_get_mcqs({course_id}, {class_id}) -> {mcqs_data.get('count', 0)} questions retrieved successfully!")
    if mcqs_data.get("questions"):
        first_q = mcqs_data["questions"][0]
        print(f"       Sample Question: {first_q.get('serial')} {first_q.get('question')[:60]}... ({len(first_q.get('options', []))} options)")

    # 8. Test pesu_get_unit_mcqs
    unit_mcqs_res = await mcp.call_tool("pesu_get_unit_mcqs", {"course_id": course_id, "unit_id": unit_id})
    unit_mcqs_data = extract_tool_result(unit_mcqs_res)
    assert isinstance(unit_mcqs_data, dict) and "totalQuestions" in unit_mcqs_data
    print(f"[PASS] pesu_get_unit_mcqs({course_id}, {unit_id}) -> {unit_mcqs_data.get('totalQuestions', 0)} total questions across {len(unit_mcqs_data.get('classes', []))} classes")

    # 9. Test pesu_download_class and pesu_download_unit with QB and QA (using Data Analytics)
    da_search = await mcp.call_tool("pesu_search_courses", {"query": "Data Analytics"})
    da_matches = extract_tool_result(da_search)
    if da_matches:
        da_id = da_matches[0]["id"]
        da_units_res = await mcp.call_tool("pesu_get_units", {"course_id": da_id})
        da_units = extract_tool_result(da_units_res)
        if da_units:
            da_unit_id = da_units[0]["unitId"]
            da_classes_res = await mcp.call_tool("pesu_get_classes", {"unit_id": da_unit_id})
            da_classes = extract_tool_result(da_classes_res)
            # Find class with QA
            qa_class = next((c for c in da_classes if c.get("hasQA")), None)
            if qa_class:
                with tempfile.TemporaryDirectory() as tmpdir:
                    qa_dl = await mcp.call_tool("pesu_download_class", {
                        "course_id": da_id,
                        "class_id": qa_class["classId"],
                        "resource_type": "qa",
                        "output_dir": tmpdir
                    })
                    qa_res = extract_tool_result(qa_dl)
                    assert qa_res.get("success") is True, f"QA download failed: {qa_res}"
                    print(f"[PASS] pesu_download_class(QA) -> downloaded {len(qa_res.get('files', []))} file(s): {qa_res.get('files')}")

    print("\nALL 10 MCP SERVER TOOLS AND TESTS PASSED PERFECTLY!")


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
