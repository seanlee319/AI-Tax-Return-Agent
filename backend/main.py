import os
import pdfplumber
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

Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_w2_data(text):
    """Parse W-2 form data from extracted text with validation"""
    if not text:
        print("Debug: No text provided to parse")
        return {"error": "No text to parse"}
    
    lines = text.split('\n')
    w2_data = {}
    
    try:
        for i, line in enumerate(lines):
            line = line.strip()
            
            if "b Employer identification number" in line and i+1 < len(lines):
                next_line = lines[i+1].strip()
                parts = next_line.split()
                
                print(f"\n=== DEBUG W-2 PARSING ===")
                print(f"Target line: {i+1}: '{next_line}'")
                print(f"Split into: {parts}")
                
                # Filter out EIN (numbers with hyphens) and count valid numbers
                numbers = [p for p in parts if p.replace('.', '').isdigit()]
                
                print(f"Found numbers: {numbers}")
                
                if len(numbers) >= 2:
                    print(f"Extracted wages: {numbers[0]}")
                    print(f"Extracted federal tax: {numbers[1]}")
                    
                    w2_data['wages_tips_other_compensation'] = float(numbers[0])
                    w2_data['federal_income_tax_withheld'] = float(numbers[1])
                else:
                    error_msg = f"Missing values. Found {len(numbers)} numbers (needed 2)"
                    print(f"ERROR: {error_msg}")
                    w2_data['error'] = error_msg
                    w2_data['raw_line'] = next_line
                
                print("=== END DEBUG ===")
                break
                
    except Exception as e:
        error_msg = f"Parsing error: {str(e)}"
        print(f"ERROR: {error_msg}")
        w2_data['error'] = error_msg
    
    return w2_data

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using pdfplumber and print all lines"""
    try:
        print("\n=== START OF EXTRACTED TEXT ===")
        
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    print(f"\n--- Page {i+1} ---")
                    lines = text.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        print(f"Line {line_num}: {line.strip()}")
        
        print("\n=== END OF EXTRACTED TEXT ===")
        return text
        
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

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
            
            file.save(filepath)
            
            # Extract text
            extracted_text = extract_text_from_pdf(filepath)
            
            # Parse W-2 specific data
            w2_data = extract_w2_data(extracted_text) if extracted_text else {}
            
            saved_files.append({
                'original_name': filename,
                'saved_name': filename,
                'extracted_text': extracted_text,
                'parsed_data': w2_data,
                'saved_path': filepath
            })
    
    return jsonify({
        'message': 'Files uploaded successfully',
        'files': saved_files
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