import os
import pdfplumber
import pytesseract
from PIL import Image
import io
import fitz
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
from flask_cors import CORS
from dataclasses import dataclass
from typing import List, Tuple

app = Flask(__name__)
CORS(app)

# Get the directory where app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Set upload folder INSIDE backend directory
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

#Extract text from scanned PDF using OCR
def extract_text_with_ocr(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        pix = page.get_pixmap()
        img = Image.open(io.BytesIO(pix.tobytes()))
        text += pytesseract.image_to_string(img) + "\n"
    return text

#Hybrid text extraction with fallback to OCR
def extract_text_from_pdf(pdf_path):
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
    
    nec_income = float(filtered_numbers[0])

    print(f"Debug - Values line: {values_line}")
    print(f"Debug - Filtered numbers: {filtered_numbers}")
    print(f"Debug - Nonemployee Compensation: {nec_income}")
    
    return nec_income

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
    
    int_income = float(filtered_numbers[0])

    print(f"Debug - Values line: {values_line}")
    print(f"Debug - Filtered numbers: {filtered_numbers}")
    print(f"Debug - Interest Income: {int_income}")
    
    return int_income
    
#Global storage for values needed for tax calculation
extracted_data_store = {
    "wages": 0.0,
    "federal_withheld": 0.0,
    "nec_income": 0.0,
    "interest_income": 0.0
}

def process_tax_document(text):
    #Process document and extract values
    if not text:
        return {"type": "unknown", "error": "Empty document"}

    # Check document type
    if "W-2" in text or "Wage and Tax Statement" in text:
        wages, federal_tax = extract_w2_values(text)
        extracted_data_store["wages"] += wages
        extracted_data_store["federal_withheld"] += federal_tax
        return {
            "type": "W-2",
            "data": {
                "wages": wages,
                "federal_income_tax_withheld": federal_tax
            }
        }
    elif "NEC" in text or "Nonemployee Compensation" in text:
        nec_income = extract_NEC(text)
        extracted_data_store["nec_income"] += nec_income
        return {
            "type": "1099-NEC",
            "data": {
                "nonemployee_compensation": nec_income
            }
        }
    elif "INT" in text or "Interest Income" in text:
        int_income = extract_INT(text)
        extracted_data_store["interest_income"] += int_income
        return {
            "type": "1099-INT",
            "data": {
                "interest_income": int_income,
            }
        }
    else:
        return {
            "type": "unknown", 
            "error": "Please upload a W-2, 1099-NEC, or a 1099-INT form",
            "data": None
        }

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
                'saved_path': filepath,
                **document_data
            })
    
    return jsonify({
        'message': 'Files uploaded successfully',
        'files': saved_files
    })

#Storage for personal info such as filing status and number of dependents
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
    
#Tax Logic
@dataclass
class TaxBracket:
    lower: float
    upper: float
    rate: float

#Tax Brackets from https://www.irs.gov/filing/federal-income-tax-rates-and-brackets
class TaxBrackets2024:    
    SINGLE = [
        TaxBracket(0, 11600, 0.10),
        TaxBracket(11601, 47150, 0.12),
        TaxBracket(47151, 100525, 0.22),
        TaxBracket(100526, 191950, 0.24),
        TaxBracket(191951, 243725, 0.32),
        TaxBracket(243726, 609350, 0.35),
        TaxBracket(609351, float('inf'), 0.37)
    ]
    
    MARRIED_JOINT = [
        TaxBracket(0, 23200, 0.10),
        TaxBracket(23201, 94300, 0.12),
        TaxBracket(94301, 201050, 0.22),
        TaxBracket(201051, 383900, 0.24),
        TaxBracket(383901, 487450, 0.32),
        TaxBracket(487451, 731200, 0.35),
        TaxBracket(731201, float('inf'), 0.37)
    ]
    
    MARRIED_SEPARATE = [
        TaxBracket(0, 11600, 0.10),
        TaxBracket(11601, 47150, 0.12),
        TaxBracket(47151, 100525, 0.22),
        TaxBracket(100526, 191950, 0.24),
        TaxBracket(191951, 243725, 0.32),
        TaxBracket(243726, 365600, 0.35),
        TaxBracket(365601, float('inf'), 0.37)
    ]
    
    HEAD_OF_HOUSEHOLD = [
        TaxBracket(0, 16550, 0.10),
        TaxBracket(16551, 63100, 0.12),
        TaxBracket(63101, 100500, 0.22),
        TaxBracket(100501, 191950, 0.24),
        TaxBracket(191951, 243700, 0.32),
        TaxBracket(243701, 609350, 0.35),
        TaxBracket(609351, float('inf'), 0.37)
    ]

    @classmethod
    def get_brackets(cls, filing_status: str) -> List[TaxBracket]:
        status_map = {
            'single': cls.SINGLE,
            'married_joint': cls.MARRIED_JOINT,
            'married_separate': cls.MARRIED_SEPARATE,
            'head_of_household': cls.HEAD_OF_HOUSEHOLD,
            'widow': cls.MARRIED_JOINT #Qualifying widows have the same tax bracket as married filiing jointly
        }
        return status_map[filing_status]
    


if __name__ == '__main__':
    app.run(debug=True)