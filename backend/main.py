import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
from flask_cors import CORS

app = Flask(__name__)

CORS(app)

# Get the directory where app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Set upload folder INSIDE backend directory
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({'error': 'No files part'}), 400
    
    files = request.files.getlist('files')
    if not files or all(file.filename == '' for file in files):
        return jsonify({'error': 'No selected files'}), 400
    
    saved_files = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            print(f"Attempting to save to: {filepath}")
            
            file.save(filepath)
            saved_files.append({
                'original_name': filename,
                'saved_name': filename,
                'saved_path': filepath
            })
    
    return jsonify({
        'message': 'Files uploaded successfully',
        'files': saved_files,
        'upload_folder': app.config['UPLOAD_FOLDER']
    })

personal_info_store = {}

@app.route('/submit-personal-info', methods=['POST'])
def submit_personal_info():
    data = request.json
    
    # Validate required fields
    if not data or 'filingStatus' not in data or 'dependents' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # Store in memory
        personal_info_store.update({
            'filingStatus': data['filingStatus'],
            'dependents': data['dependents']
        })
        
        print("Current stored personal info:", personal_info_store)
        
        return jsonify({
            'message': 'Personal information saved',
            'data': personal_info_store
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)