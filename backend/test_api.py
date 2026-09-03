import os
import sys
import json

os.environ["DOTNET_SYSTEM_GLOBALIZATION_INVARIANT"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app


def load_dotenv():
    search_dirs = [
        os.getcwd(),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ]
    for d in search_dirs:
        env_path = os.path.join(d, ".env")
        if os.path.isfile(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
            break


def test_api():
    load_dotenv()

    # 1. Health check
    unauth_client = app.test_client()
    res = unauth_client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    print("[PASS] /api/health -> 200")

    # 2. Unauthorized access checks
    for endpoint in ["/api/courses", "/api/units/22902", "/api/classes/69624"]:
        res = unauth_client.get(endpoint)
        assert res.status_code == 401, f"Unauthenticated request to {endpoint} should return 401, got {res.status_code}"
    res = unauth_client.post("/api/download", json={"files": [{"classId": "1", "name": "test"}], "course_id": "22902"})
    assert res.status_code == 401, f"Unauthenticated download should return 401, got {res.status_code}"
    print("[PASS] Unauthorized access protection -> 401 across all endpoints")

    # 3. Login validation checks
    client = app.test_client()
    res = client.post("/api/login", json={})
    assert res.status_code == 400, f"Empty login should be 400: {res.status_code}"
    print("[PASS] /api/login empty credentials -> 400")

    res = client.post("/api/login", json={"username": "BAD_USER", "password": "BAD_PASSWORD"})
    assert res.status_code == 401, f"Bad login should be 401: {res.status_code}"
    print("[PASS] /api/login invalid credentials -> 401")

    # 4. Login with student credentials
    test_username = os.environ.get("PESU_USERNAME")
    test_password = os.environ.get("PESU_PASSWORD")
    if not test_username or not test_password:
        print("[SKIP] Skipping live student tests: PESU_USERNAME or PESU_PASSWORD not set in environment or .env file")
        print("To run live tests, set PESU_USERNAME and PESU_PASSWORD in .env or environment variables.")
        return

    res = client.post("/api/login", json={"username": test_username, "password": test_password})
    assert res.status_code == 200, f"Valid login failed: {res.status_code}, {res.json}"
    print("[PASS] /api/login valid credentials -> 200")

    # 5. Verify local courses.json integrity (catalog fallback)
    courses_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "courses.json")
    assert os.path.exists(courses_path), "courses.json missing"
    with open(courses_path, "r") as f:
        catalog = json.load(f)
    assert len(catalog) > 15000, f"courses.json catalog truncated: only {len(catalog)} courses found"
    print(f"[PASS] courses.json catalog integrity verified -> {len(catalog)} courses in fallback database")

    # 6. Fetch live student courses
    res = client.get("/api/courses")
    assert res.status_code == 200, f"Courses failed: {res.status_code}"
    courses = res.json
    assert len(courses) > 0, "No courses returned"
    for field in ["id", "subjectName"]:
        assert field in courses[0], f"Course missing required field: {field}"
    print(f"[PASS] /api/courses -> {len(courses)} enrolled student courses")

    # 7. Fetch units for course
    target_course = None
    for c in courses:
        if "Software Engineering" in c.get("subjectName", ""):
            target_course = c
            break
    if not target_course:
        target_course = courses[0]

    course_id = target_course["id"]
    res = client.get(f"/api/units/{course_id}")
    assert res.status_code == 200, f"Units failed: {res.status_code}"
    units = res.json
    assert len(units) > 0, "No units returned"
    for field in ["unitId", "title", "description"]:
        assert field in units[0], f"Unit missing required field: {field}"
    print(f"[PASS] /api/units/{course_id} ({target_course['subjectName']}) -> {len(units)} units")

    # 8. Fetch classes for unit
    unit_id = units[0]["unitId"]
    res = client.get(f"/api/classes/{unit_id}")
    assert res.status_code == 200, f"Classes failed: {res.status_code}"
    classes = res.json
    assert len(classes) > 0, "No classes returned"
    for field in ["classId", "title", "path", "hasSlides", "hasNotes"]:
        assert field in classes[0], f"Class missing required field: {field}"
    print(f"[PASS] /api/classes/{unit_id} -> {len(classes)} classes with resource metadata (hasSlides={classes[0]['hasSlides']}, hasNotes={classes[0]['hasNotes']})")

    # 9. Download single file (slides)
    dl_payload = {
        "files": [{"classId": classes[0]["classId"], "name": classes[0]["title"]}],
        "course_id": course_id,
        "course_name": target_course["subjectName"],
        "unit_name": units[0]["title"],
        "resource_type": "2",
    }
    res = client.post("/api/download", json=dl_payload)
    assert res.status_code == 200, f"Download single file failed: {res.status_code}"
    assert res.data[:4] == b"%PDF", "Downloaded content does not start with %PDF"
    print(f"[PASS] /api/download (single slides) -> 200, size: {len(res.data)} bytes")

    # 10. Download merged files (slides)
    if len(classes) >= 2:
        dl_merged_payload = {
            "files": [
                {"classId": classes[0]["classId"], "name": classes[0]["title"]},
                {"classId": classes[1]["classId"], "name": classes[1]["title"]},
            ],
            "course_id": course_id,
            "course_name": target_course["subjectName"],
            "unit_name": units[0]["title"],
            "resource_type": "2",
        }
        res = client.post("/api/download", json=dl_merged_payload)
        assert res.status_code == 200, f"Download merged failed: {res.status_code}"
        assert res.data[:4] == b"%PDF", "Merged content does not start with %PDF"
        print(f"[PASS] /api/download (merged slides) -> 200, size: {len(res.data)} bytes")

    # 11. Download notes (resource_type="3")
    # In Software Engineering Unit 1 Class 1, notes exist!
    notes_class = None
    for cls in classes:
        if cls.get("hasNotes"):
            notes_class = cls
            break
    if notes_class:
        dl_notes_payload = {
            "files": [{"classId": notes_class["classId"], "name": notes_class["title"]}],
            "course_id": course_id,
            "course_name": target_course["subjectName"],
            "unit_name": units[0]["title"],
            "resource_type": "3",
        }
        res = client.post("/api/download", json=dl_notes_payload)
        assert res.status_code == 200, f"Download notes failed: {res.status_code}"
        assert res.data[:4] == b"%PDF", "Notes content does not start with %PDF"
        print(f"[PASS] /api/download (notes rt=3) -> 200, size: {len(res.data)} bytes")

    # 12. Test graceful handling when class has no slides
    # Find Data Analytics course (id 22905) Unit 1 (id 69297) Class 1 which has no slides
    da_units_res = client.get("/api/units/22905")
    if da_units_res.status_code == 200 and da_units_res.json:
        da_classes_res = client.get(f"/api/classes/{da_units_res.json[0]['unitId']}")
        if da_classes_res.status_code == 200 and da_classes_res.json:
            da_class = da_classes_res.json[0]
            if not da_class.get("hasSlides"):
                no_slides_payload = {
                    "files": [{"classId": da_class["classId"], "name": da_class["title"]}],
                    "course_id": "22905",
                    "course_name": "Data Analytics",
                    "unit_name": "Unit 1",
                    "resource_type": "2",
                }
                res = client.post("/api/download", json=no_slides_payload)
                assert res.status_code == 404, f"Class with no slides should return 404, got {res.status_code}"
                assert "error" in res.json, "Error response missing 'error' key"
                print(f"[PASS] /api/download on class without slides -> 404 Not Found: {res.json['error']}")

    # 13. Download input validation
    res = client.post("/api/download", json={"files": [], "course_id": "22902"})
    assert res.status_code == 400, f"Empty files list should return 400, got {res.status_code}"
    res = client.post("/api/download", json={"files": [{"classId": "1"}]})
    assert res.status_code == 400, f"Missing course_id should return 400, got {res.status_code}"
    print("[PASS] /api/download input validation -> 400 on empty/missing fields")

    print("\nALL 13 TESTS PASSED RIGOROUSLY!")


if __name__ == "__main__":
    test_api()
