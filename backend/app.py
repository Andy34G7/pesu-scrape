from flask import Flask, jsonify, request, session
from flask_cors import CORS
from pesu_client import PESUClient
import os
import os
# Set this BEFORE importing any library that relies on .NET (like Spire) via pdf_utils check
os.environ['DOTNET_SYSTEM_GLOBALIZATION_INVARIANT'] = '1'

import json

app = Flask(__name__, static_folder='static', static_url_path='/')

@app.route('/')
def serve():
    return app.send_static_file('index.html')

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Not found"}), 404
    return app.send_static_file('index.html')
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24)) # Required for session management
CORS(app, supports_credentials=True) # Enable CORS for all routes with credentials

# Global client store (simple version for single user demo, ideally use session-based storage or redis)
# For a multi-user web app, we shouldn't store the client globally like this.
# Instead, we should probably re-create the session or store cookies.
# However, since we can't easily serialize the requests.Session object, 
# we will store a map of session_id -> PESUClient.
clients = {}

def get_authenticated_client():
    user_id = session.get('user_id')
    if not user_id or user_id not in clients:
        return None
    client = clients[user_id]
    if not getattr(client, 'is_authenticated', False):
        return None
    return client

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "PESU Scrape Backend is running"})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if 'user_id' not in session:
        session['user_id'] = os.urandom(16).hex()
    
    user_id = session['user_id']
    client = PESUClient()
    
    success, message = client.authenticate(username, password)
    
    if success:
        clients[user_id] = client
        return jsonify({"status": "success", "message": message})
    else:
        clients.pop(user_id, None)
        return jsonify({"status": "error", "message": message}), 401

@app.route('/api/courses', methods=['GET'])
def get_courses():
    try:
        client = get_authenticated_client()
        if not client:
            return jsonify({"error": "Unauthorized or session expired"}), 401
            
        courses = client.get_subjects()
        
        # Fallback to local courses.json only if live fetch returns nothing
        if not courses:
            courses_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'courses.json')
            if os.path.exists(courses_path):
                try:
                    with open(courses_path, 'r') as f:
                        courses = json.load(f)
                except Exception as json_e:
                    print(f"Error reading courses.json: {json_e}")
        
        return jsonify(courses)
            
    except Exception as e:
        print(f"Error fetching courses: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/units/<course_id>', methods=['GET'])
def get_units(course_id):
    client = get_authenticated_client()
    if not client:
        return jsonify({"error": "Unauthorized or session expired"}), 401
    
    clean_course_id = str(course_id).strip().replace('\\', '').replace('"', '').replace("'", '')
    units = client.get_units(clean_course_id)
    return jsonify(units)

@app.route('/api/classes/<unit_id>', methods=['GET'])
def get_classes(unit_id):
    client = get_authenticated_client()
    if not client:
        return jsonify({"error": "Unauthorized or session expired"}), 401
    
    clean_unit_id = str(unit_id).strip().replace('\\', '').replace('"', '').replace("'", '')
    classes = client.get_classes(clean_unit_id)
    return jsonify(classes)

@app.route('/api/download', methods=['POST'])
def download_merged():
    client = get_authenticated_client()
    if not client:
        return jsonify({"error": "Unauthorized or session expired"}), 401
    
    data = request.json or {}
    files_to_download = data.get('files', []) 
    course_id = data.get('course_id')
    course_name = data.get('course_name', 'Course')
    unit_name = data.get('unit_name', 'Unit')
    resource_type = data.get('resource_type', '2')
    
    if not files_to_download or not course_id:
        return jsonify({"error": "No files or course ID selected"}), 400

    user_id = session['user_id']
    
    import tempfile
    base_temp = tempfile.gettempdir()
    temp_dir = os.path.join(base_temp, f"pesu_temp_{user_id}")
    os.makedirs(temp_dir, exist_ok=True)
    
    from pdf_utils import convert_pptx_to_pdf, convert_docx_to_pdf, convert_image_to_pdf, merge_pdfs
    import concurrent.futures
    import shutil
    import zipfile

    def process_file(file_info):
        class_id = file_info.get('classId')
        name = file_info.get('name', 'unknown')
        
        print(f"Downloading file: {name} (Class ID: {class_id}, Type: {resource_type})")
        
        temp_path = os.path.join(temp_dir, f"{class_id}_temp")
        success, final_paths = client.download_file(course_id, class_id, temp_path, resource_type)
        
        processed_pdfs = []
        
        if success:
            for final_path in final_paths:
                print(f"Successfully downloaded to {final_path}")
                is_pdf = False
                
                try:
                    with open(final_path, 'rb') as f:
                        header = f.read(4)
                        if header.startswith(b'%PDF'):
                            is_pdf = True
                except Exception as e:
                    print(f"Error reading file header: {e}")

                if is_pdf:
                    if not final_path.endswith('.pdf'):
                        new_path = final_path + ".pdf"
                        os.rename(final_path, new_path)
                    else:
                        new_path = final_path
                    processed_pdfs.append(new_path)
                else:
                    is_img = False
                    try:
                        with open(final_path, 'rb') as f:
                            h = f.read(8)
                            if h.startswith(b'\xff\xd8') or h.startswith(b'\x89PNG\r\n\x1a\n') or h.startswith(b'GIF8'):
                                is_img = True
                    except Exception:
                        pass

                    if is_img:
                        pdf_path = os.path.splitext(final_path)[0] + ".pdf"
                        if convert_image_to_pdf(final_path, pdf_path):
                            processed_pdfs.append(pdf_path)
                        continue

                    is_zip = False
                    try:
                        with open(final_path, 'rb') as f:
                            header = f.read(2)
                            if header == b'PK':
                                is_zip = True
                    except Exception:
                        pass
                        
                    if is_zip:
                        try:
                            with zipfile.ZipFile(final_path, 'r') as z:
                                filenames = z.namelist()
                                if any(f.startswith('ppt/') for f in filenames):
                                    pptx_path = final_path if final_path.endswith('.pptx') else final_path + ".pptx"
                                    if pptx_path != final_path:
                                        os.rename(final_path, pptx_path)
                                    pdf_path = os.path.splitext(pptx_path)[0] + ".pdf"
                                    if convert_pptx_to_pdf(pptx_path, pdf_path):
                                        processed_pdfs.append(pdf_path)
                                elif any(f.startswith('word/') for f in filenames):
                                    docx_path = final_path if final_path.endswith('.docx') else final_path + ".docx"
                                    if docx_path != final_path:
                                        os.rename(final_path, docx_path)
                                    pdf_path = os.path.splitext(docx_path)[0] + ".pdf"
                                    if convert_docx_to_pdf(docx_path, pdf_path):
                                        processed_pdfs.append(pdf_path)
                                else:
                                    print(f"Unknown zip content for {name}")
                        except Exception as e:
                            print(f"Error inspecting zip for {name}: {e}")
                    else:
                        print(f"File {name} is not a PDF, image, or Office file")
        else:
            print(f"Failed to download {name}")
            
        return processed_pdfs

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(process_file, files_to_download))

    downloaded_pdfs = [pdf for sublist in results for pdf in sublist]
            
    if not downloaded_pdfs:
        shutil.rmtree(temp_dir, ignore_errors=True)
        res_label = "notes" if str(resource_type) == "3" else "slides"
        return jsonify({"error": f"No {res_label} found or available to download for the selected class(es)."}), 404
        
    import re
    safe_course_name = re.sub(r'[^\w\-_.]', '_', course_name)
    safe_unit_name = re.sub(r'[^\w\-_.]', '_', unit_name)
    output_filename = f"{safe_course_name}_{safe_unit_name}.pdf"
    output_path = os.path.join(temp_dir, output_filename)
    
    try:
        merge_pdfs(downloaded_pdfs, output_path)
        
        from flask import send_file
        response = send_file(output_path, as_attachment=True, download_name=output_filename)
        
        @response.call_on_close
        def cleanup():
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"Error cleaning up temp_dir: {e}")

        return response
        
    except Exception as e:
        print(f"Error merging PDFs: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"error": "Failed to merge PDFs"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)



