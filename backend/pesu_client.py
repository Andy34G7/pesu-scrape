import requests
import json
from flask import session
from bs4 import BeautifulSoup
import re

BASE_URL = "https://www.pesuacademy.com/Academy"

class PESUClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def _extract_csrf_token(self, html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        csrf_input = soup.find("input", {"name": "_csrf"})
        if csrf_input:
            return csrf_input.get("value")
        return None

    def authenticate(self, username, password):
        try:
            # Initial request to get CSRF token
            response = self.session.get(BASE_URL)
            if response.status_code != 200:
                return False, "Failed to reach PESU Academy"

            csrf_token = self._extract_csrf_token(response.text)
            if not csrf_token:
                # Sometimes it might not be there if already logged in or different page structure
                # But for a fresh session it should be there.
                # Let's try proceeding without it or logging a warning
                print("Warning: CSRF token not found")
                # return False, "CSRF token not found" 

            payload = {
                'j_username': username,
                'j_password': password,
                '_csrf': csrf_token
            }
            
            login_url = f"{BASE_URL}/j_spring_security_check"
            response = self.session.post(login_url, data=payload)
            
            # Check for successful login
            # PESU usually redirects to /Academy/s/studentProfilePESU or similar on success
            # On failure, it might redirect to login_error=1
            
            if "Invalid credentials" in response.text or "login_error=1" in response.url:
                return False, "Invalid credentials"
            
            # Validate by trying to access profile
            profile_url = f"{BASE_URL}/s/studentProfilePESU"
            profile_response = self.session.get(profile_url, allow_redirects=False)
            
            if profile_response.status_code in (302, 301):
                 # If it redirects back to login, then auth failed
                 if "login" in profile_response.headers.get('Location', ''):
                     return False, "Login validation failed"

            return True, "Login successful"
        except Exception as e:
            return False, f"Login error: {str(e)}"

    def get_subjects(self):
        url = f"{BASE_URL}/a/g/getSubjectsCode"
        response = self.session.get(url)
        if response.status_code == 200:
            # The response is HTML options, we need to parse it if we want to use it directly
            # But the reference code parses it.
            # However, the user also has courses.json.
            # Let's parse it to be safe/dynamic.
            soup = BeautifulSoup(response.text, "html.parser")
            options = soup.find_all("option")
            courses = []
            for option in options:
                val = option.get("value")
                name = option.text.strip()
                if val and name:
                     # Clean ID like in reference
                    clean_id = str(val).strip().replace('\\"', '').replace("\\'", '').strip('"').strip("'").replace('\\', '')
                    courses.append({"id": clean_id, "subjectName": name})
            return courses
        return []

    def get_units(self, course_id):
        url = f"{BASE_URL}/a/i/getCourse/{course_id}"
        response = self.session.get(url)
        if response.status_code == 200:
            # Parse HTML options
            content = response.json() if response.headers.get('Content-Type', '').startswith('application/json') else response.text
            soup = BeautifulSoup(content, "html.parser")
            options = soup.find_all("option")
            units = []
            for option in options:
                val = option.get("value")
                name = option.text.strip()
                if val and name:
                    clean_id = str(val).strip().replace('\\', '').strip('"').strip("'")
                    units.append({"unitId": clean_id, "title": name, "description": name})
            return units
        return []

    def get_classes(self, unit_id):
        url = f"{BASE_URL}/a/i/getCourseClasses/{unit_id}"
        response = self.session.get(url)
        if response.status_code == 200:
            content = response.json() if response.headers.get('Content-Type', '').startswith('application/json') else response.text
            soup = BeautifulSoup(content, "html.parser")
            options = soup.find_all("option")
            classes = []
            for option in options:
                val = option.get("value")
                name = option.text.strip()
                if val and name:
                    clean_id = str(val).strip().replace('\\', '').strip('"').strip("'")
                    classes.append({"classId": clean_id, "title": name, "path": clean_id}) # path here is actually the unitid/classid for download
            return classes
        return []
        
    def download_file(self, course_id, class_id, output_path, resource_type="2"):
        # Logic adapted from goat-scraper
        url = f"{BASE_URL}/s/studentProfilePESUAdmin"
        params = {
            "url": "studentProfilePESUAdmin",
            "controllerMode": "6403",
            "actionType": "60",
            "selectedData": course_id,
            "id": resource_type,
            "unitid": class_id
        }
        
        try:
            response = self.session.get(url, params=params, stream=True)
            content_type = response.headers.get('Content-Type', '')
            
            if 'application/pdf' in content_type or \
               'application/vnd.openxmlformats-officedocument.presentationml.presentation' in content_type or \
               'application/vnd.ms-powerpoint' in content_type or \
               'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type or \
               'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type or \
               'application/msword' in content_type or \
               'application/octet-stream' in content_type or \
               'binary/octet-stream' in content_type:
                
                # Try to get filename from Content-Disposition
                filename = None
                if 'Content-Disposition' in response.headers:
                    import cgi
                    _, params = cgi.parse_header(response.headers['Content-Disposition'])
                    filename = params.get('filename')
                
                final_output_path = output_path
                if filename:
                     # Clean filename
                     filename = os.path.basename(filename)
                     dir_name = os.path.dirname(output_path)
                     final_output_path = os.path.join(dir_name, filename)
                     
                # Direct download
                with open(final_output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True, [final_output_path]
            
            elif 'text/html' in content_type:
                # Parse for download link
                soup = BeautifulSoup(response.text, "html.parser")
                download_urls = []
                
                # Check for loadIframe or downloadslidecoursedoc or downloadcoursedoc
                for link in soup.find_all(['a', 'div', 'span', 'i', 'p']):
                    onclick = link.get('onclick', '')
                    href = link.get('href', '')
                    
                    url_to_add = None
                    if 'downloadslidecoursedoc' in onclick:
                        match = re.search(r"loadIframe\('([^']+)'", onclick)
                        if match:
                            url_to_add = match.group(1)
                    elif 'downloadslidecoursedoc' in href:
                        url_to_add = href
                    elif 'downloadcoursedoc' in onclick:
                        match = re.search(r"downloadcoursedoc\(['\"]([^'\"]+)['\"]\)", onclick)
                        if match:
                            doc_id = match.group(1)
                            # Updated URL based on user feedback (step 160)
                            url_to_add = f"/Academy/a/referenceMeterials/downloadslidecoursedoc/{doc_id}"
                    
                    if url_to_add:
                        # Normalize URL
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
                            
                        # Download actual file
                        file_response = self.session.get(full_url, stream=True)
                        
                        # Use index suffix if multiple files, otherwise keep original output_path for backward compat/single file
                        current_output_path = output_path if len(download_urls) == 1 else f"{output_path}_{i}"
                        
                        with open(current_output_path, 'wb') as f:
                            for chunk in file_response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        downloaded_paths.append(current_output_path)
                        
                    return True, downloaded_paths
                else:
                    print(f"No download link found for {class_id}")
                    return False, []
            else:
                print(f"Unknown content type: {content_type}")
                return False, []

        except Exception as e:
            print(f"Download error: {e}")
            return False, []


