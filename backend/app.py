from flask import Flask, jsonify, request, session
from flask_cors import CORS
from pesu_client import PESUClient
import os
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
app.secret_key = os.urandom(24) # Required for session management
CORS(app, supports_credentials=True) # Enable CORS for all routes with credentials

# Global client store (simple version for single user demo, ideally use session-based storage or redis)
# For a multi-user web app, we shouldn't store the client globally like this.
# Instead, we should probably re-create the session or store cookies.
# However, since we can't easily serialize the requests.Session object, 
# we will store a map of session_id -> PESUClient.
clients = {}

def get_client(session_id):
    if session_id not in clients:
        clients[session_id] = PESUClient()
    return clients[session_id]

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "PESU Scrape Backend is running"})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    # Create a new client for this session
    # In a real app, we'd manage session IDs properly. 
    # Here we'll just use the Flask session ID or generate one.
    if 'user_id' not in session:
        session['user_id'] = os.urandom(16).hex()
    
    user_id = session['user_id']
    client = get_client(user_id)
    
    success, message = client.authenticate(username, password)
    
    if success:
        return jsonify({"status": "success", "message": message})
    else:
        return jsonify({"status": "error", "message": message}), 401

@app.route('/api/courses', methods=['GET'])
def get_courses():
    try:
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401
            
        user_id = session['user_id']
        client = get_client(user_id)
        courses = client.get_subjects()
        return jsonify(courses)
            
    except Exception as e:
        print(f"Error fetching courses: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/units/<course_id>', methods=['GET'])
def get_units(course_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    client = get_client(user_id)
    units = client.get_units(course_id)
    return jsonify(units)

@app.route('/api/classes/<unit_id>', methods=['GET'])
def get_classes(unit_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    client = get_client(user_id)
    classes = client.get_classes(unit_id)
    return jsonify(classes)

@app.route('/api/download', methods=['POST'])
def download_merged():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    files_to_download = data.get('files', []) 
    course_id = data.get('course_id') # Needed for download
    course_name = data.get('course_name', 'Course')
    unit_name = data.get('unit_name', 'Unit')
    
    resource_type = data.get('resource_type', '2') # Default to Slides (2)
    
    if not files_to_download or not course_id:
        return jsonify({"error": "No files or course ID selected"}), 400

    user_id = session['user_id']
    client = get_client(user_id)
    
    # Create temp directory using absolute path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(base_dir, f"temp_{user_id}")
    os.makedirs(temp_dir, exist_ok=True)
    
    downloaded_pdfs = []
    
    from pdf_utils import convert_pptx_to_pdf, convert_docx_to_pdf, merge_pdfs
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
                
                # Detect file type
                try:
                    with open(final_path, 'rb') as f:
                        header = f.read(4)
                        if header.startswith(b'%PDF'):
                            is_pdf = True
                except Exception as e:
                    print(f"Error reading file header: {e}")

                if is_pdf:
                    new_path = final_path + ".pdf"
                    os.rename(final_path, new_path)
                    processed_pdfs.append(new_path)
                else:
                    # Try PPTX/DOCX conversion
                    is_zip = False
                    try:
                        with open(final_path, 'rb') as f:
                            header = f.read(2)
                            if header == b'PK':
                                is_zip = True
                    except:
                        pass
                        
                    if is_zip:
                        # Inspect zip contents to determine type
                        try:
                            with zipfile.ZipFile(final_path, 'r') as z:
                                filenames = z.namelist()
                                if any(f.startswith('ppt/') for f in filenames):
                                    # It's likely a PPTX
                                    pptx_path = final_path + ".pptx"
                                    os.rename(final_path, pptx_path)
                                    pdf_path = pptx_path.replace('.pptx', '.pdf')
                                    if convert_pptx_to_pdf(pptx_path, pdf_path):
                                        processed_pdfs.append(pdf_path)
                                elif any(f.startswith('word/') for f in filenames):
                                    # It's likely a DOCX
                                    docx_path = final_path + ".docx"
                                    os.rename(final_path, docx_path)
                                    pdf_path = docx_path.replace('.docx', '.pdf')
                                    if convert_docx_to_pdf(docx_path, pdf_path):
                                        processed_pdfs.append(pdf_path)
                                else:
                                    # Fallback or unknown zip
                                    print(f"Unknown zip content for {name}")
                        except Exception as e:
                            print(f"Error inspecting zip for {name}: {e}")
                    else:
                            print(f"File {name} is not a PDF or Office file")
        else:
            print(f"Failed to download {name}")
            
        return processed_pdfs

    # Use ThreadPoolExecutor for parallel downloads
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(process_file, files_to_download))
    
    # Flatten results
    downloaded_pdfs = [pdf for sublist in results for pdf in sublist]
            
    if not downloaded_pdfs:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"error": "Failed to download or convert any files"}), 500
        
    output_filename = f"{course_name}_{unit_name}.pdf".replace(" ", "_")
    output_path = os.path.join(temp_dir, output_filename)
    
    try:
        merge_pdfs(downloaded_pdfs, output_path)
        
        from flask import send_file, after_this_request
        
        @after_this_request
        def remove_temp_dir(response):
            try:
                # We can't delete the file we are sending immediately, but we can delete the temp dir contents
                # Or we can stream the file into memory and delete everything.
                # For simplicity, let's keep the temp dir for now or use a background task.
                # But since we are sending a file from temp_dir, we can't delete temp_dir yet.
                # A better approach is to stream the file.
                pass
            except Exception as e:
                print(f"Error cleaning up: {e}")
            return response

        return send_file(output_path, as_attachment=True)
        
    except Exception as e:
        print(f"Error merging PDFs: {e}")
        return jsonify({"error": "Failed to merge PDFs"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)



