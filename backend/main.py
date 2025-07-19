import os
import pdfplumber
import pytesseract
from PIL import Image
import io
import fitz
import re
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

Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

def extract_text_with_ocr(pdf_path):
    """Extract text from scanned PDF using OCR"""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        pix = page.get_pixmap()
        img = Image.open(io.BytesIO(pix.tobytes()))
        text += pytesseract.image_to_string(img) + "\n"
    return text

def extract_text_from_pdf(pdf_path):
    """Hybrid text extraction with fallback to OCR"""
    try:
        # First try regular text extraction
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        
        # If we get less text (likely scanned PDF), try OCR
        if len(text.strip()) < 50:
            return extract_text_with_ocr(pdf_path)
        return text
    except Exception as e:
        print(f"PDF text extraction failed: {e}")
        return extract_text_with_ocr(pdf_path)

def extract_w2_values(text):
    if not text:
        return None, None
    
    # Split text into lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Find the line containing the labels
    label_line = None
    for i, line in enumerate(lines):
        if ("Employer identification" in line or 
            "Wages, tips" in line or 
            "Federal income tax" in line):
            label_line = i
            break
    
    if label_line is None or label_line + 1 >= len(lines):
        return None, None
    
    # Get the next line after labels
    values_line = lines[label_line + 1]
    parts = values_line.split()
    
    # Filter out EIN (numbers with hyphens)
    filtered_numbers = [part for part in parts if '-' not in part]
    
    # We need exactly 2 values remaining
    if len(filtered_numbers) != 2:
        return None, None

    wages = float(filtered_numbers[0])
    federal_tax = float(filtered_numbers[1])
    
    print(f"Debug - Values line: {values_line}")
    print(f"Debug - Filtered numbers: {filtered_numbers}")
    print(f"Debug - Wages: {wages}, Federal Tax: {federal_tax}")
    
    return wages, federal_tax

def extract_NEC(text):
    if not text:
        return None
    
    # Split text into lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Find the line containing the labels
    label_line = None
    for i, line in enumerate(lines):
        if ("Copy" in line):
            label_line = i
            break
        
    if label_line is None or label_line + 1 >= len(lines):
        return None
    
    # Get the next line after labels
    values_line = lines[label_line + 1]
    parts = values_line.split()
    
    # Filter out EIN and SSN (numbers with hyphens)
    filtered_numbers = [part for part in parts if '-' not in part and '$' not in part]
    
    # We need exactly 1 value remaining
    if len(filtered_numbers) != 1:
        return None
    
    nonempComp = float(filtered_numbers[0])

    print(f"Debug - Values line: {values_line}")
    print(f"Debug - Filtered numbers: {filtered_numbers}")
    print(f"Debug - Nonemployee Compensation: {nonempComp}")
    
    return nonempComp

def extract_INT(text):
    if not text:
        return None
    
    # Split text into lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Find the line containing the labels
    label_line = None
    for i, line in enumerate(lines):
        if ("$" in line):
            label_line = i
            break
        
    if label_line is None or label_line + 1 >= len(lines):
        return None
    
    # Get the next line after labels
    values_line = lines[label_line]
    parts = values_line.split()
    
    # Filter out evrything before '$'
    filtered_numbers = parts[parts.index('$') + 1:] if '$' in parts else []
    
    filtered_numbers = [
        x for x in filtered_numbers
        if str(x).replace('.', '', 2).isdigit()
        and '-' not in str(x)  # Also exclude hyphenated numbers (like SSN/EIN)
    ]

    # Remove last occurrence of '2024' if it exists
    if '2024' in filtered_numbers:
        last_2024_index = len(filtered_numbers) - 1 - filtered_numbers[::-1].index('2024')
        filtered_numbers.pop(last_2024_index)
    
    # We need exactly 1 value remaining
    if len(filtered_numbers) != 1:
        return None
    
    intIncome = float(filtered_numbers[0])

    print(f"Debug - Values line: {values_line}")
    print(f"Debug - Filtered numbers: {filtered_numbers}")
    print(f"Debug - Interest Income: {intIncome}")
    
    return intIncome
    

def process_tax_document(text):
    """Process document and extract values if it's a W-2 form"""
    if not text:
        return {"type": "unknown", "data": None}
    
    # Check if this is a W-2 form
    if "W-2" in text or "Wage and Tax Statement" in text:
        print("Detected W-2 form")
        wages, federal_tax = extract_w2_values(text)
        return {
            "type": "W-2",
            "data": {
                "wages": wages,
                "federal_income_tax_withheld": federal_tax
            }
        }
    # Then check for 1099-NEC
    elif "NEC" in text or "Nonemployee Compensation" in text:
        print("Detected 1099-NEC form")
        nonemp_comp = extract_NEC(text)
        return {
            "type": "1099-NEC",
            "data": {
                "nonemployee_compensation": nonemp_comp
            }
        }
    # Check for 1099-INT
    elif "INT" in text or "Interest Income" in text:
        print("Detected 1099-INT form")
        intIncome = extract_INT(text)
        return {
            "type": "1099-INT",
            "data": {
                "interest_income": intIncome,
            }
        }
    else:
        print("Not a W-2 form")
        return {"type": "unknown", "data": None}


@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({'error': 'No files part'}), 400
    
    files = request.files.getlist('files')
    if not files or all(file.filename == '' for file in files):
        return jsonify({'error': 'No selected files'}), 400
    
    saved_files = []
    
    for file in files:
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            file.save(filepath)
            
            # Extract text using hybrid approach
            extracted_text = extract_text_from_pdf(filepath)

            # Process the document
            document_data = process_tax_document(extracted_text)

            #Print to terminal for debugging
            # print("\n" + "="*50)
            # print(f"EXTRACTED TEXT FROM: {filename}")
            # print("="*50)
            # print(extracted_text)
            # print("="*50 + "\n")
            
            saved_files.append({
                'original_name': filename,
                'saved_name': filename,
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