# app.py (Flask backend)
from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
import pdfplumber  # For PDF text extraction

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({'error': 'No files part'}), 400
    
    files = request.files.getlist('files')
    if not files or all(file.filename == '' for file in files):
        return jsonify({'error': 'No selected files'}), 400
    
    results = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Extract text from PDF (basic implementation)
            text = ""
            try:
                with pdfplumber.open(filepath) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() + "\n"
            except Exception as e:
                return jsonify({'error': f'Error processing {filename}: {str(e)}'}), 500
            
            results.append({
                'filename': filename,
                'text': text,
                'message': 'File processed successfully'
            })
        else:
            return jsonify({'error': f'Invalid file type for {file.filename}'}), 400
    
    return jsonify({'results': results}), 200

@app.route('/submit-personal-info', methods=['POST'])
def submit_personal_info():
    data = request.json
    # Validate required fields
    required_fields = ['filingStatus', 'dependents']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Here you would typically store this info for tax calculation
    return jsonify({
        'message': 'Personal information received',
        'data': data
    }), 200

if __name__ == '__main__':
    app.run(debug=True)