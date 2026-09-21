import os
import sys
import re
import json
import logging
from urllib.parse import unquote
import concurrent.futures
import requests
from bs4 import BeautifulSoup

# Configure logger to output only to stderr so stdio MCP JSON-RPC protocol is never corrupted
logger = logging.getLogger("pesu_client")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

BASE_URL = "https://www.pesuacademy.com/Academy"


class PESUClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.csrf_token = None
        self.is_authenticated = False
        self._username = None
        self._password = None
        self._cached_courses = None
        self._cached_units = {}
        self._cached_classes = {}

    def _extract_csrf_token(self, html_content):
        if not html_content:
            return None
        soup = BeautifulSoup(html_content, "html.parser")
        csrf_input = soup.find("input", {"name": "_csrf"})
        if csrf_input and csrf_input.get("value"):
            return csrf_input.get("value")
        csrf_meta = soup.find("meta", {"name": "csrf-token"})
        if csrf_meta and csrf_meta.get("content"):
            return csrf_meta.get("content")
        return None

    def _ensure_csrf_token(self):
        if not self.csrf_token:
            try:
                profile_url = f"{BASE_URL}/s/studentProfilePESU"
                resp = self.session.get(profile_url, timeout=10)
                if resp.status_code == 200:
                    self.csrf_token = self._extract_csrf_token(resp.text)
                    if self.csrf_token:
                        self.session.headers.update({
                            "X-CSRF-TOKEN": self.csrf_token,
                            "X-CSRF-Token": self.csrf_token,
                            "X-Requested-With": "XMLHttpRequest",
                            "Referer": f"{BASE_URL}/s/studentProfilePESU"
                        })
            except Exception as e:
                logger.warning(f"Failed to refresh CSRF token: {e}")
        return self.csrf_token

    def is_session_alive(self) -> bool:
        if not self.is_authenticated:
            return False
        try:
            profile_url = f"{BASE_URL}/s/studentProfilePESU"
            resp = self.session.get(profile_url, allow_redirects=False, timeout=5)
            if resp.status_code == 200 and "j_spring_security_check" not in resp.text:
                return True
        except Exception:
            pass
        return False

    def _reauthenticate_if_needed(self) -> bool:
        if self._username and self._password:
            logger.info("Session expired or invalid. Auto re-authenticating with saved credentials...")
            ok, msg = self.authenticate(self._username, self._password)
            return ok
        return False

    def authenticate(self, username, password):
        try:
            self.is_authenticated = False
            self._username = username
            self._password = password

            # Initial request to get CSRF token
            response = self.session.get(BASE_URL, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to reach PESU Academy: HTTP {response.status_code}")
                return False, "Failed to reach PESU Academy"

            csrf_token = self._extract_csrf_token(response.text)
            if not csrf_token:
                logger.warning("Initial CSRF token not found on home page")

            payload = {
                'j_username': username,
                'j_password': password,
                '_csrf': csrf_token
            }
            
            login_url = f"{BASE_URL}/j_spring_security_check"
            response = self.session.post(login_url, data=payload, timeout=10)
            
            if "Invalid credentials" in response.text or "authfailed" in response.url or "login_error" in response.url:
                logger.error("Authentication failed: Invalid credentials")
                return False, "Invalid credentials"
            
            # Validate by accessing profile
            profile_url = f"{BASE_URL}/s/studentProfilePESU"
            profile_response = self.session.get(profile_url, allow_redirects=False, timeout=10)
            
            if profile_response.status_code in (301, 302, 303, 307):
                logger.error("Login validation failed: Redirect detected")
                return False, "Login validation failed (session redirect)"

            if profile_response.status_code != 200:
                logger.error(f"Login validation failed: HTTP {profile_response.status_code}")
                return False, f"Login validation failed: HTTP {profile_response.status_code}"

            self.csrf_token = self._extract_csrf_token(profile_response.text)
            if self.csrf_token:
                self.session.headers.update({
                    "X-CSRF-TOKEN": self.csrf_token,
                    "X-CSRF-Token": self.csrf_token,
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": f"{BASE_URL}/s/studentProfilePESU"
                })

            self.is_authenticated = True
            # Reset session caches on fresh authentication
            self._cached_courses = None
            self._cached_units = {}
            self._cached_classes = {}

            logger.info(f"Successfully authenticated as {username}")
            return True, "Login successful"
        except Exception as e:
            self.is_authenticated = False
            logger.error(f"Login error: {e}")
            return False, f"Login error: {str(e)}"

    def get_subjects(self, force_refresh=False):
        if self._cached_courses is not None and not force_refresh:
            return self._cached_courses

        self._ensure_csrf_token()

        all_courses = []
        try:
            sem_url = f"{BASE_URL}/s/studentProfile/getStudentSemestersPESU"
            sem_resp = self.session.get(sem_url, timeout=10)
            if sem_resp.status_code == 200:
                content = sem_resp.text.strip()
                if content.startswith('"') and content.endswith('"'):
                    try:
                        content = json.loads(content)
                    except Exception:
                        pass

                soup = BeautifulSoup(content, "html.parser")
                semesters = []
                for opt in soup.find_all("option"):
                    val = opt.get("value")
                    if val:
                        clean_val = re.sub(r'[^\w-]', '', str(val)).strip()
                        if clean_val:
                            semesters.append((clean_val, opt.text.strip()))

                def fetch_semester_courses(sem):
                    sem_id, sem_title = sem
                    form_data = {
                        "controllerMode": 6403,
                        "actionType": 38,
                        "id": sem_id,
                        "menuId": 653,
                        "_csrf": self.csrf_token
                    }
                    headers = {"X-CSRF-TOKEN": self.csrf_token} if self.csrf_token else {}
                    try:
                        resp = self.session.post(f"{BASE_URL}/s/studentProfilePESUAdmin", data=form_data, headers=headers, timeout=10)
                        if resp.status_code != 200:
                            return []
                        s = BeautifulSoup(resp.text, "html.parser")
                        rows = s.find_all("tr", id=lambda x: x and x.startswith("rowWiseCourseContent_"))
                        sem_courses = []
                        for row in rows:
                            cid = row.get("id", "").replace("rowWiseCourseContent_", "").strip()
                            tds = row.find_all("td")
                            code = tds[0].get_text(strip=True) if len(tds) > 0 else ""
                            name = tds[1].get_text(strip=True) if len(tds) > 1 else ""
                            full_name = f"{code} - {name}" if code and not name.startswith(code) else (name or code)
                            full_name = " ".join(full_name.split())
                            sem_courses.append({
                                "id": cid,
                                "subjectCode": code,
                                "subjectName": full_name,
                                "semester": sem_title
                            })
                        return sem_courses
                    except Exception as sem_err:
                        logger.warning(f"Error fetching courses for sem {sem_id}: {sem_err}")
                        return []

                if semesters:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                        course_lists = list(executor.map(fetch_semester_courses, semesters))

                    seen_ids = set()
                    for clist in course_lists:
                        for c in clist:
                            if c["id"] not in seen_ids:
                                seen_ids.add(c["id"])
                                all_courses.append(c)

        except Exception as e:
            logger.error(f"Error scraping live subjects: {e}")

        # Fallback to local courses.json database if live scraping returns empty
        if not all_courses:
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            courses_path = os.path.join(backend_dir, "courses.json")
            if os.path.exists(courses_path):
                try:
                    with open(courses_path, "r", encoding="utf-8") as f:
                        catalog = json.load(f)
                        logger.info(f"Loaded {len(catalog)} courses from fallback catalog database")
                        all_courses = catalog
                except Exception as json_err:
                    logger.error(f"Failed to load fallback courses.json: {json_err}")

        self._cached_courses = all_courses
        return all_courses

    def get_units(self, course_id):
        course_id = str(course_id).strip().replace("\\", "").replace('"', '').replace("'", '')
        if course_id in self._cached_units:
            return self._cached_units[course_id]

        params = {
            "controllerMode": 6403,
            "actionType": 42,
            "id": course_id,
            "menuId": 653
        }
        try:
            url = f"{BASE_URL}/s/studentProfilePESUAdmin"
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch units for course {course_id}: status {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            units = []
            seen_unit_ids = set()
            for a in soup.find_all("a"):
                onclick = a.get("onclick", "")
                if "handleclassUnit" in onclick:
                    m = re.search(r"handleclassUnit\(['\"]?([a-zA-Z0-9_-]+)['\"]?\)", onclick)
                    if m:
                        unit_id = m.group(1)
                        if unit_id not in seen_unit_ids:
                            seen_unit_ids.add(unit_id)
                            raw_title = a.get_text(strip=True)
                            clean_title = " ".join(raw_title.split())
                            units.append({
                                "unitId": unit_id,
                                "title": clean_title,
                                "description": clean_title
                            })

            self._cached_units[course_id] = units
            return units
        except Exception as e:
            logger.error(f"Error fetching units for course {course_id}: {e}")
            return []

    def get_classes(self, unit_id):
        unit_id = str(unit_id).strip().replace("\\", "").replace('"', '').replace("'", '')
        if unit_id in self._cached_classes:
            return self._cached_classes[unit_id]

        params = {
            "controllerMode": 6403,
            "actionType": 43,
            "coursecontentid": unit_id
        }
        try:
            url = f"{BASE_URL}/s/studentProfilePESUAdmin"
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch classes for unit {unit_id}: status {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table")
            if not table:
                return []

            col_indices = {}
            thead = table.find("thead")
            if thead:
                for idx, th in enumerate(thead.find_all("th")):
                    th_id = str(th.get("id", "")).strip()
                    th_text = th.get_text(strip=True).lower()
                    if th_id == "2" or "slide" in th_text:
                        col_indices["slides"] = idx
                    elif th_id == "3" or "note" in th_text:
                        col_indices["notes"] = idx
                    elif th_id == "8" or "mcq" in th_text:
                        col_indices["mcqs"] = idx
                    elif th_id == "6" or "qb" in th_text or "question bank" in th_text:
                        col_indices["qb"] = idx
                    elif th_id == "7" or "qa" in th_text or "question answer" in th_text or "question and answer" in th_text:
                        col_indices["qa"] = idx
                    elif th_id == "5" or "assignment" in th_text:
                        col_indices["assignments"] = idx

            rows = table.find("tbody").find_all("tr") if table.find("tbody") else table.find_all("tr")[1:]
            classes = []
            seen_class_ids = set()

            for row in rows:
                tds = row.find_all("td")
                if not tds:
                    continue
                raw_title = tds[0].get_text(strip=True)
                clean_title = " ".join(raw_title.split())

                class_id = None
                for el in row.find_all(True):
                    onclick = el.get("onclick", "")
                    if "handleclasscoursecontentunit" in onclick:
                        m = re.search(r"handleclasscoursecontentunit\(([^)]+)\)", onclick)
                        if m:
                            args = [arg.strip().strip("'").strip('"') for arg in m.group(1).split(",")]
                            if args and args[0]:
                                class_id = args[0]
                                break

                if not class_id or class_id in seen_class_ids:
                    continue

                seen_class_ids.add(class_id)

                has_slides = False
                has_notes = False
                has_mcqs = False
                has_qb = False
                has_qa = False
                slides_count = 0
                notes_count = 0
                mcqs_count = 0
                qb_count = 0
                qa_count = 0

                if "slides" in col_indices and col_indices["slides"] < len(tds):
                    slides_td = tds[col_indices["slides"]]
                    stext = slides_td.get_text(strip=True).replace("*", "")
                    has_slides = slides_td.find("a") is not None or (stext != "-" and stext != "")
                    try:
                        slides_count = int(stext) if stext.isdigit() else (1 if has_slides else 0)
                    except Exception:
                        slides_count = 1 if has_slides else 0

                if "notes" in col_indices and col_indices["notes"] < len(tds):
                    notes_td = tds[col_indices["notes"]]
                    ntext = notes_td.get_text(strip=True).replace("*", "")
                    has_notes = notes_td.find("a") is not None or (ntext != "-" and ntext != "")
                    try:
                        notes_count = int(ntext) if ntext.isdigit() else (1 if has_notes else 0)
                    except Exception:
                        notes_count = 1 if has_notes else 0

                if "mcqs" in col_indices and col_indices["mcqs"] < len(tds):
                    mcqs_td = tds[col_indices["mcqs"]]
                    mtext = mcqs_td.get_text(strip=True).replace("*", "")
                    has_mcqs = mcqs_td.find("a") is not None or (mtext != "-" and mtext != "")
                    try:
                        mcqs_count = int(mtext) if mtext.isdigit() else (1 if has_mcqs else 0)
                    except Exception:
                        mcqs_count = 1 if has_mcqs else 0

                if "qb" in col_indices and col_indices["qb"] < len(tds):
                    qb_td = tds[col_indices["qb"]]
                    qbtext = qb_td.get_text(strip=True).replace("*", "")
                    has_qb = qb_td.find("a") is not None or (qbtext != "-" and qbtext != "")
                    try:
                        qb_count = int(qbtext) if qbtext.isdigit() else (1 if has_qb else 0)
                    except Exception:
                        qb_count = 1 if has_qb else 0

                if "qa" in col_indices and col_indices["qa"] < len(tds):
                    qa_td = tds[col_indices["qa"]]
                    qatext = qa_td.get_text(strip=True).replace("*", "")
                    has_qa = qa_td.find("a") is not None or (qatext != "-" and qatext != "")
                    try:
                        qa_count = int(qatext) if qatext.isdigit() else (1 if has_qa else 0)
                    except Exception:
                        qa_count = 1 if has_qa else 0

                classes.append({
                    "classId": class_id,
                    "title": clean_title,
                    "path": class_id,
                    "hasSlides": has_slides,
                    "hasNotes": has_notes,
                    "hasMCQs": has_mcqs,
                    "hasQB": has_qb,
                    "hasQA": has_qa,
                    "slidesCount": slides_count,
                    "notesCount": notes_count,
                    "mcqsCount": mcqs_count,
                    "qbCount": qb_count,
                    "qaCount": qa_count
                })

            self._cached_classes[unit_id] = classes
            return classes
        except Exception as e:
            logger.error(f"Error fetching classes for unit {unit_id}: {e}")
            return []

    def get_mcqs(self, course_id, class_id):
        """
        Fetch and parse Multiple Choice Questions (MCQs) for a specific class.
        Endpoint: /Academy/s/studentProfilePESUAdmin with actionType=60 and id=8.
        Returns:
          Dict with 'courseId', 'classId', 'count', and 'questions' list.
        """
        course_id = str(course_id).strip().replace("\\", "").replace('"', '').replace("'", '')
        class_id = str(class_id).strip().replace("\\", "").replace('"', '').replace("'", '')

        url = f"{BASE_URL}/s/studentProfilePESUAdmin"
        params = {
            "url": "studentProfilePESUAdmin",
            "controllerMode": "6403",
            "actionType": "60",
            "selectedData": course_id,
            "id": "8",
            "unitid": class_id
        }
        try:
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch MCQs for class {class_id}: HTTP {response.status_code}")
                return {
                    "courseId": course_id,
                    "classId": class_id,
                    "count": 0,
                    "questions": [],
                    "message": f"HTTP {response.status_code}"
                }

            soup = BeautifulSoup(response.text, "html.parser")
            mcq_container = soup.find(id="courseMaterialMCQs")
            if not mcq_container or "No MCQs Content" in response.text or "No\n\t\t\t\t\t\tMCQs" in response.text:
                return {
                    "courseId": course_id,
                    "classId": class_id,
                    "count": 0,
                    "questions": [],
                    "message": "No MCQs available for this class"
                }

            questions = []
            elem_sets = mcq_container.find_all("div", class_="qstn-elem-set")
            for elem in elem_sets:
                q_serial_el = elem.find("div", class_="qstn-serial")
                serial_str = q_serial_el.get_text(strip=True) if q_serial_el else ""
                q_content_el = elem.find("div", class_="qstn-content")
                q_text = " ".join(q_content_el.get_text(strip=True).split()) if q_content_el else ""

                options = []
                curr = elem.find_next_sibling()
                while curr and "qstn-elem-set" not in curr.get("class", []):
                    radio = curr.find("div", class_="radio") or (curr if "radio" in curr.get("class", []) else None)
                    if radio:
                        inp = radio.find("input", {"type": "radio"})
                        is_correct = False
                        ans_id = ""
                        q_id = ""
                        if inp:
                            is_correct = (inp.get("value") == "true")
                            ans_id = inp.get("id", "").replace("ans_", "")
                            q_id = inp.get("name", "").replace("ans_", "")

                        label = radio.find("label")
                        opt_text = ""
                        if label:
                            for input_tag in label.find_all("input"):
                                input_tag.decompose()
                            opt_text = " ".join(label.get_text(strip=True).split())

                        options.append({
                            "option": opt_text,
                            "isCorrect": is_correct,
                            "answerId": ans_id,
                            "questionId": q_id
                        })
                    curr = curr.find_next_sibling()

                if q_text:
                    questions.append({
                        "serial": serial_str,
                        "question": q_text,
                        "options": options
                    })

            return {
                "courseId": course_id,
                "classId": class_id,
                "count": len(questions),
                "questions": questions
            }
        except Exception as e:
            logger.error(f"Error parsing MCQs for class {class_id}: {e}")
            return {
                "courseId": course_id,
                "classId": class_id,
                "count": 0,
                "questions": [],
                "error": str(e)
            }

    def get_unit_mcqs(self, course_id, unit_id):
        """
        Fetch all MCQs across all classes in a syllabus unit.
        """
        course_id = str(course_id).strip().replace("\\", "").replace('"', '').replace("'", '')
        unit_id = str(unit_id).strip().replace("\\", "").replace('"', '').replace("'", '')

        classes = self.get_classes(unit_id)
        if not classes:
            return {
                "courseId": course_id,
                "unitId": unit_id,
                "totalQuestions": 0,
                "classes": []
            }

        eligible_classes = [c for c in classes if c.get("hasMCQs", True)]

        def fetch_class_mcqs(cls):
            res = self.get_mcqs(course_id, cls["classId"])
            return {
                "classId": cls["classId"],
                "title": cls.get("title", ""),
                "count": res.get("count", 0),
                "questions": res.get("questions", [])
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(fetch_class_mcqs, eligible_classes))

        populated_classes = [r for r in results if r["count"] > 0]
        total_q = sum(r["count"] for r in populated_classes)

        return {
            "courseId": course_id,
            "unitId": unit_id,
            "totalQuestions": total_q,
            "classes": populated_classes
        }

    def download_file(self, course_id, class_id, output_path, resource_type="2"):
        url = f"{BASE_URL}/s/studentProfilePESUAdmin"
        params = {
            "url": "studentProfilePESUAdmin",
            "controllerMode": "6403",
            "actionType": "60",
            "selectedData": str(course_id).strip(),
            "id": str(resource_type).strip(),
            "unitid": str(class_id).strip()
        }
        
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            response = self.session.get(url, params=params, stream=True, timeout=30)
            content_type = response.headers.get('Content-Type', '')

            def extract_filename(cd_header):
                if not cd_header:
                    return None
                m = re.search(r'''filename\*=UTF-8''([^\;]+)|filename=["']?([^"';]+)["']?''', cd_header, re.I)
                if m:
                    fn = m.group(1) or m.group(2)
                    clean_fn = os.path.basename(unquote(fn).strip().replace('\\', '/'))
                    return clean_fn if clean_fn else None
                return None

            from pdf_utils import detect_file_type

            if any(mime in content_type for mime in [
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/msword',
                'application/octet-stream',
                'binary/octet-stream'
            ]):
                filename = extract_filename(response.headers.get('Content-Disposition'))
                final_output_path = output_path
                if filename:
                    dir_name = os.path.dirname(output_path)
                    final_output_path = os.path.join(dir_name, filename)
                     
                with open(final_output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Ensure proper extension if missing
                if not os.path.splitext(final_output_path)[1]:
                    detected_ext = detect_file_type(final_output_path)
                    if detected_ext:
                        new_path = f"{final_output_path}{detected_ext}"
                        os.rename(final_output_path, new_path)
                        final_output_path = new_path

                return True, [final_output_path]
            
            elif 'text/html' in content_type:
                soup = BeautifulSoup(response.text, "html.parser")
                download_urls = []
                
                for link in soup.find_all(['a', 'div', 'span', 'i', 'p', 'iframe', 'embed', 'button', 'li']):
                    onclick = link.get('onclick', '')
                    href = link.get('href', '')
                    src = link.get('src', '')
                    
                    url_to_add = None
                    if 'downloadslidecoursedoc' in onclick:
                        match = re.search(r"loadIframe\(['\"]([^'\"]+)", onclick)
                        if match:
                            url_to_add = match.group(1)
                    elif 'downloadslidecoursedoc' in href:
                        url_to_add = href
                    elif 'downloadslidecoursedoc' in src:
                        url_to_add = src
                    elif 'downloadcoursedoc' in onclick or 'downloadcoursedocforstudent' in onclick:
                        match = re.search(r"downloadcoursedoc(?:forstudent)?\(['\"]([^'\"]+)['\"]\)", onclick)
                        if match:
                            doc_id = match.group(1)
                            url_to_add = f"/Academy/s/referenceMeterials/downloadcoursedoc/{doc_id}"
                    elif 'downloadcoursedoc' in href or 'downloadcoursedocforstudent' in href:
                        match = re.search(r"downloadcoursedoc(?:forstudent)?\(['\"]([^'\"]+)['\"]\)", href)
                        if match:
                            doc_id = match.group(1)
                            url_to_add = f"/Academy/s/referenceMeterials/downloadcoursedoc/{doc_id}"
                    elif 'handleDownloadReadingMaterial' in onclick:
                        match = re.search(r"handleDownloadReadingMaterial\(['\"]([^'\"]+)['\"]\)", onclick)
                        if match:
                            url_to_add = f"/Academy/s/studentProfilePESUAdmin/material/{match.group(1)}"
                    elif 'handleDownloadCourseInfo' in onclick:
                        match = re.search(r"handleDownloadCourseInfo\(['\"]([^'\"]+)['\"]\)", onclick)
                        if match:
                            url_to_add = f"/Academy/s/studentProfilePESUAdmin/courseinfo/{match.group(1)}"
                    elif href and href.startswith('http') and not href.startswith('javascript:'):
                        url_to_add = href
                    elif src and src.startswith('http'):
                        url_to_add = src
                    
                    if url_to_add:
                        url_to_add = url_to_add.split('#')[0]
                        if url_to_add not in download_urls:
                            download_urls.append(url_to_add)
                
                if download_urls:
                    downloaded_paths = []
                    for i, download_url in enumerate(download_urls):
                        if download_url.startswith('/Academy'):
                            full_url = f"https://www.pesuacademy.com{download_url}"
                        elif download_url.startswith('http'):
                            full_url = download_url
                        else:
                            full_url = f"{BASE_URL}/{download_url.lstrip('/')}"
                            
                        file_response = self.session.get(full_url, stream=True, timeout=30)
                        if file_response.status_code == 200:
                            base_path = output_path if len(download_urls) == 1 else f"{output_path}_{i}"
                            fn = extract_filename(file_response.headers.get('Content-Disposition'))
                            if fn and '.' in fn:
                                ext = os.path.splitext(fn)[1]
                                current_output_path = f"{base_path}{ext}"
                            else:
                                current_output_path = base_path

                            with open(current_output_path, 'wb') as f:
                                for chunk in file_response.iter_content(chunk_size=8192):
                                    f.write(chunk)

                            # Auto-detect extension from magic bytes if not present
                            if not os.path.splitext(current_output_path)[1]:
                                detected_ext = detect_file_type(current_output_path)
                                if detected_ext:
                                    new_path = f"{current_output_path}{detected_ext}"
                                    os.rename(current_output_path, new_path)
                                    current_output_path = new_path

                            if os.path.exists(current_output_path) and os.path.getsize(current_output_path) > 0:
                                downloaded_paths.append(current_output_path)
                    
                    if downloaded_paths:
                        return True, downloaded_paths
                    else:
                        logger.warning(f"Failed to download valid files from URLs: {download_urls}")
                        return False, []
                else:
                    logger.warning(f"No download link found for class {class_id}")
                    return False, []
            else:
                logger.warning(f"Unknown content type: {content_type}")
                return False, []

        except Exception as e:
            logger.error(f"Download error for class {class_id}: {e}")
            return False, []
