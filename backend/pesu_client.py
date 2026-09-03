import os
import re
from urllib.parse import unquote
import concurrent.futures
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.pesuacademy.com/Academy"

class PESUClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.csrf_token = None
        self.is_authenticated = False
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
            profile_url = f"{BASE_URL}/s/studentProfilePESU"
            resp = self.session.get(profile_url)
            if resp.status_code == 200:
                self.csrf_token = self._extract_csrf_token(resp.text)
                if self.csrf_token:
                    self.session.headers.update({"X-CSRF-TOKEN": self.csrf_token})
        return self.csrf_token

    def authenticate(self, username, password):
        try:
            self.is_authenticated = False
            # Initial request to get CSRF token
            response = self.session.get(BASE_URL)
            if response.status_code != 200:
                return False, "Failed to reach PESU Academy"

            csrf_token = self._extract_csrf_token(response.text)
            if not csrf_token:
                print("Warning: Initial CSRF token not found")

            payload = {
                'j_username': username,
                'j_password': password,
                '_csrf': csrf_token
            }
            
            login_url = f"{BASE_URL}/j_spring_security_check"
            response = self.session.post(login_url, data=payload)
            
            if "Invalid credentials" in response.text or "authfailed" in response.url or "login_error" in response.url:
                return False, "Invalid credentials"
            
            # Validate by accessing profile
            profile_url = f"{BASE_URL}/s/studentProfilePESU"
            profile_response = self.session.get(profile_url, allow_redirects=False)
            
            if profile_response.status_code in (301, 302, 303, 307):
                return False, "Login validation failed"

            if profile_response.status_code != 200:
                return False, f"Login validation failed: HTTP {profile_response.status_code}"

            self.csrf_token = self._extract_csrf_token(profile_response.text)
            if self.csrf_token:
                self.session.headers.update({"X-CSRF-TOKEN": self.csrf_token})

            self.is_authenticated = True
            # Reset session caches on fresh authentication
            self._cached_courses = None
            self._cached_units = {}
            self._cached_classes = {}

            return True, "Login successful"
        except Exception as e:
            self.is_authenticated = False
            return False, f"Login error: {str(e)}"

    def get_subjects(self, force_refresh=False):
        if self._cached_courses is not None and not force_refresh:
            return self._cached_courses

        self._ensure_csrf_token()

        try:
            sem_url = f"{BASE_URL}/s/studentProfile/getStudentSemestersPESU"
            sem_resp = self.session.get(sem_url)
            if sem_resp.status_code != 200:
                print(f"Failed to fetch semesters: status {sem_resp.status_code}")
                return []

            content = sem_resp.text.strip()
            if content.startswith('"') and content.endswith('"'):
                try:
                    import json
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

            if not semesters:
                print("No semesters found in getStudentSemestersPESU")
                return []

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
                resp = self.session.post(f"{BASE_URL}/s/studentProfilePESUAdmin", data=form_data, headers=headers)
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

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                course_lists = list(executor.map(fetch_semester_courses, semesters))

            all_courses = []
            seen_ids = set()
            for clist in course_lists:
                for c in clist:
                    if c["id"] not in seen_ids:
                        seen_ids.add(c["id"])
                        all_courses.append(c)

            self._cached_courses = all_courses
            return all_courses

        except Exception as e:
            print(f"Error getting subjects: {e}")
            return []

    def get_units(self, course_id):
        course_id = str(course_id).strip().replace('\\', '').replace('"', '').replace("'", '')
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
            response = self.session.get(url, params=params)
            if response.status_code != 200:
                print(f"Failed to fetch units for course {course_id}: status {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            units = []
            seen_unit_ids = set()
            for a in soup.find_all("a"):
                onclick = a.get("onclick", "")
                if "handleclassUnit" in onclick:
                    m = re.search(r"handleclassUnit\([\"']?(\w+)[\"']?\)", onclick)
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
            print(f"Error fetching units for course {course_id}: {e}")
            return []

    def get_classes(self, unit_id):
        unit_id = str(unit_id).strip().replace('\\', '').replace('"', '').replace("'", '')
        if unit_id in self._cached_classes:
            return self._cached_classes[unit_id]

        params = {
            "controllerMode": 6403,
            "actionType": 43,
            "coursecontentid": unit_id
        }
        try:
            url = f"{BASE_URL}/s/studentProfilePESUAdmin"
            response = self.session.get(url, params=params)
            if response.status_code != 200:
                print(f"Failed to fetch classes for unit {unit_id}: status {response.status_code}")
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
                slides_count = 0
                notes_count = 0

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

                classes.append({
                    "classId": class_id,
                    "title": clean_title,
                    "path": class_id,
                    "hasSlides": has_slides,
                    "hasNotes": has_notes,
                    "slidesCount": slides_count,
                    "notesCount": notes_count
                })

            self._cached_classes[unit_id] = classes
            return classes
        except Exception as e:
            print(f"Error fetching classes for unit {unit_id}: {e}")
            return []

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
            response = self.session.get(url, params=params, stream=True)
            content_type = response.headers.get('Content-Type', '')

            def extract_filename(cd_header):
                if not cd_header:
                    return None
                m = re.search(r'''filename\*=UTF-8''([^;]+)|filename=["']?([^"';]+)["']?''', cd_header, re.I)
                if m:
                    fn = m.group(1) or m.group(2)
                    clean_fn = os.path.basename(unquote(fn).strip().replace('\\', '/'))
                    return clean_fn if clean_fn else None
                return None

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
                return True, [final_output_path]
            
            elif 'text/html' in content_type:
                soup = BeautifulSoup(response.text, "html.parser")
                download_urls = []
                
                for link in soup.find_all(['a', 'div', 'span', 'i', 'p', 'iframe', 'embed']):
                    onclick = link.get('onclick', '')
                    href = link.get('href', '')
                    src = link.get('src', '')
                    
                    url_to_add = None
                    if 'downloadslidecoursedoc' in onclick:
                        match = re.search(r"loadIframe\('([^']+)'", onclick)
                        if match:
                            url_to_add = match.group(1)
                    elif 'downloadslidecoursedoc' in href:
                        url_to_add = href
                    elif 'downloadslidecoursedoc' in src:
                        url_to_add = src
                    elif 'downloadcoursedoc' in onclick:
                        match = re.search(r"downloadcoursedoc\(['\"]([^'\"]+)['\"]\)", onclick)
                        if match:
                            doc_id = match.group(1)
                            url_to_add = f"/Academy/a/referenceMeterials/downloadslidecoursedoc/{doc_id}"
                    elif 'downloadcoursedoc' in href:
                        match = re.search(r"downloadcoursedoc/([a-zA-Z0-9_-]+)", href)
                        if match:
                            doc_id = match.group(1)
                            url_to_add = f"/Academy/a/referenceMeterials/downloadslidecoursedoc/{doc_id}"
                    
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
                            
                        file_response = self.session.get(full_url, stream=True)
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
                            if os.path.exists(current_output_path) and os.path.getsize(current_output_path) > 0:
                                downloaded_paths.append(current_output_path)
                    
                    if downloaded_paths:
                        return True, downloaded_paths
                    else:
                        print(f"Failed to download valid files from URLs: {download_urls}")
                        return False, []
                else:
                    print(f"No download link found for class {class_id}")
                    return False, []
            else:
                print(f"Unknown content type: {content_type}")
                return False, []

        except Exception as e:
            print(f"Download error: {e}")
            return False, []



