import os
import shutil
import pdfplumber
import pytesseract
from PIL import Image
import io
import fitz
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
from flask_cors import CORS
from dataclasses import dataclass
from typing import List, Tuple
from PyPDF2 import PdfReader, PdfWriter

app = Flask(__name__)
CORS(app)

# Get the directory where app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Set upload folder INSIDE backend directory
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

# Clear uploads folder on startup
if os.path.exists(UPLOAD_FOLDER):
    shutil.rmtree(UPLOAD_FOLDER)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#Show Uploaded Files
@app.route('/get-uploaded-files', methods=['GET'])
def get_uploaded_files():
    try:
        files = []
        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                files.append({
                    'name': filename,
                    'size': os.path.getsize(filepath),
                    'upload_time': os.path.getmtime(filepath)
                })
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

#Clear the 'uploads' file on refresh
@app.route('/clear-uploads', methods=['POST'])
def clear_uploads():
    try:
        if os.path.exists(UPLOAD_FOLDER):
            shutil.rmtree(UPLOAD_FOLDER)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Reset the data storage
        extracted_data_store["wages"] = 0.0
        extracted_data_store["federal_withheld"] = 0.0
        extracted_data_store["nec_income"] = 0.0
        extracted_data_store["interest_income"] = 0.0

        return jsonify({'success': True, 'message': 'Uploads folder cleared'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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

#Reset the values for tax calculation
@app.route('/reset-data-store', methods=['POST'])
def reset_data_store():
    try:
        extracted_data_store["wages"] = 0.0
        extracted_data_store["federal_withheld"] = 0.0
        extracted_data_store["nec_income"] = 0.0
        extracted_data_store["interest_income"] = 0.0
        return jsonify({'success': True, 'message': 'Data store reset successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
            
            # Check if file already exists (skip if true)
            if os.path.exists(filepath):
                saved_files.append({
                    'original_name': filename,
                    'saved_name': filename,
                    'saved_path': filepath,
                    'status': 'skipped',
                    'message': 'File already exists'
                })
                continue

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
            # print(personal_info_store)

            saved_files.append({
                'original_name': filename,
                'saved_name': filename,
                'saved_path': filepath,
                'status': 'processed',
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
    if not data or 'filingStatus' not in data or 'dependentChildren' not in data or 'otherDependents' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # Store in memory
        personal_info_store.update({
            'filingStatus': data['filingStatus'],
            'dependentChildren': data['dependentChildren'],
            'otherDependents': data['otherDependents']
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
    
# Tax deductions based on filinig status
STANDARD_DEDUCTIONS = {
    'single': 14600,
    'married_joint': 29200,
    'married_separate': 14600,
    'head_of_household': 21900,
    'widow': 29200
}

CHILD_TAX_CREDIT = 2000
OTHER_DEPENDENT_CREDIT = 500

PHASE_OUT_THRESHOLDS = {
    'single': 200000,
    'married_joint': 400000,
    'married_separate': 200000,
    'head_of_household': 200000,
    'widow': 400000
}
PHASE_OUT_RATE = 0.05

def calculate_dependent_credits(filing_status: str, dependent_children: int, other_dependents: int, adjusted_gross_income: float):
    # Calculate raw credits
    child_credit = dependent_children * CHILD_TAX_CREDIT
    other_credit = other_dependents * OTHER_DEPENDENT_CREDIT
    total_raw_credit = child_credit + other_credit
    
    # Apply phase-out if income exceeds threshold
    threshold = PHASE_OUT_THRESHOLDS[filing_status]
    if adjusted_gross_income <= threshold:
        return total_raw_credit
    
    excess_income = adjusted_gross_income - threshold
    phase_out_amount = (excess_income // 1000) * 50
    phased_out_credit = max(total_raw_credit - phase_out_amount, 0)
    
    print(f"Debug - Phase-out calculation:")
    print(f"  AGI: {adjusted_gross_income}, Threshold: {threshold}")
    print(f"  Excess: {excess_income}, Phase-out: {phase_out_amount}")
    print(f"  Raw credit: {total_raw_credit}, Final credit: {phased_out_credit}")
    
    return phased_out_credit

def calculate_tax(taxable_income: float, filing_status: str) -> float:
    """Calculate tax based on taxable income and filing status."""
    brackets = TaxBrackets2024.get_brackets(filing_status)
    tax = 0.0

    for bracket in brackets:
        if taxable_income > bracket.lower:
            bracket_amount = min(taxable_income, bracket.upper) - bracket.lower
            tax += bracket_amount * bracket.rate
        else:
            break  # No more income to tax
    
    return tax

def calculate_total_tax(total_income: float, filing_status: str, dependent_children: int = 0, other_dependents: int = 0) -> Tuple[float, float]:
    """Calculate total tax including credits."""
    # Calculate taxable income after standard deduction
    standard_deduction = STANDARD_DEDUCTIONS[filing_status]
    taxable_income = max(total_income - standard_deduction, 0)
    
    # Calculate tax before credits
    tax_before_credits = calculate_tax(taxable_income, filing_status)
    
    # Calculate dependent credits with phase-out
    dependent_credits = calculate_dependent_credits(
        filing_status, 
        dependent_children, 
        other_dependents, 
        total_income
    )
    
    # Apply credits (can't reduce tax below zero)
    final_tax = max(tax_before_credits - dependent_credits, 0)
    
    return tax_before_credits, final_tax, dependent_credits

@app.route('/calculate-tax', methods=['GET'])
def calculate_tax_endpoint():
    try:
        # Get income from all sources (initialize to 0 if missing)
        wages = extracted_data_store.get("wages", 0.0)
        nec_income = extracted_data_store.get("nec_income", 0.0)
        interest_income = extracted_data_store.get("interest_income", 0.0)
        total_income = wages + nec_income + interest_income
        
        if not personal_info_store:
            return jsonify({'error': 'Personal information missing'}), 400
            
        # Calculate tax
        tax_no_credits, tax_owed, credits = calculate_total_tax(
            total_income,
            personal_info_store['filingStatus'],
            personal_info_store['dependentChildren'],
            personal_info_store['otherDependents']
        )
        
        federal_withheld = extracted_data_store.get("federal_withheld", 0.0)
        refund_or_due = federal_withheld - tax_owed
        
        # Generate filled 1040 form
        filled_form_path = fill_1040_form(
            wages=wages,
            federal_withheld=federal_withheld,
            nec_income = nec_income,
            interest_income = interest_income,
            total_income=total_income,
            tax_no_credits = tax_no_credits,
            tax_owed=tax_owed,
            refund_or_due=refund_or_due,
            filing_status=personal_info_store['filingStatus'],
            dependent_children=personal_info_store['dependentChildren'],
            other_dependents=personal_info_store['otherDependents']
        )
        
        return jsonify({
            'success': True,
            'results': {
                'total_income': total_income,
                'tax_owed': tax_owed,
                'federal_withheld': federal_withheld,
                'refund_or_due': refund_or_due,
                'credits_applied': credits,
                'breakdown': {  # Ensure this always exists
                    'wages': wages,
                    'nec_income': nec_income,
                    'interest_income': interest_income
                },
                'form_generated': bool(filled_form_path)
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def fill_1040_form(wages: float, nec_income: float, interest_income: float,
                   federal_withheld: float, total_income: float, 
                   tax_no_credits: float, tax_owed: float, refund_or_due: float, 
                   filing_status: str, dependent_children: int, other_dependents: int):
    try:
        # Create outputs directory
        outputs_dir = os.path.join(BASE_DIR, 'outputs')
        os.makedirs(outputs_dir, exist_ok=True)
        
        # File paths
        template_path = os.path.join(BASE_DIR, '1040_template.pdf')
        output_path = os.path.join(outputs_dir, 'filled_1040.pdf')
        
        # Read template
        reader = PdfReader(template_path)
        writer = PdfWriter()
        
        # Copy pages
        for page in reader.pages:
            writer.add_page(page)
            
        # Calculate values
        standard_deduction = STANDARD_DEDUCTIONS.get(filing_status, 14600)
        taxable_income = max(total_income - standard_deduction, 0)
        total_credits = (dependent_children * CHILD_TAX_CREDIT) + (other_dependents * OTHER_DEPENDENT_CREDIT)
        
        # Field mappings - using the actual field names from your template
        field_values = {
            # Page 1 - Income
            'f1_32[0]': f"{wages:.2f}",                # Wages (line 1a)
            'f1_43[0]': f"{interest_income:.2f}",      # Taxable interest (line 2b)
            'f1_53[0]': f"{nec_income:.2f}",           # Nonemployee Compensation (line 8)
            'f1_54[0]': f"{total_income:.2f}",         # Total income (line 9)
            'f1_57[0]': f"{standard_deduction:.2f}",   # Standard deduction (line 12)
            'f1_59[0]': f"{standard_deduction:.2f}",   # Standard deduction (line 14)
            'f1_60[0]': f"{taxable_income:.2f}",       # Taxable income (line 15)
            
            # Page 2 - Tax
            'f2_02[0]': f"{tax_no_credits:.2f}",       # Tax (line 16)
            'f2_04[0]': f"{tax_no_credits:.2f}",       # Total tax (line 18)
            'f2_05[0]': f"{total_credits:.2f}",        # Credits (line 19)
            'f2_07[0]': f"{total_credits:.2f}",        # Total Credits (line 21)
            'f2_10[0]': f"{tax_owed:.2f}",             # Total tax (line 24)
            
            # Payments
            'f2_11[0]': f"{federal_withheld:.2f}",     # Federal withheld (line 25a)
            'f2_14[0]': f"{federal_withheld:.2f}",     # Total Federal withheld (line 25d)
            'f2_22[0]': f"{federal_withheld:.2f}",     # Total payments (line 33)
        }

        # Handle refund/amount due
        if refund_or_due >= 0:
            field_values.update({
                'f2_23[0]': f"{refund_or_due:.2f}",   # Amount overpaid (line 34)
                'f2_24[0]': f"{refund_or_due:.2f}"    # Refund amount (line 35a)
            })
        else:
            field_values.update({
                'f2_28[0]': f"{-refund_or_due:.2f}",  # Amount due (line 37)
                'f2_29[0]': f"{-refund_or_due:.2f}"   # Amount you owe (line 38)
            })

        # Update fields
        for page in writer.pages:
            writer.update_page_form_field_values(
                page,
                {k: v for k, v in field_values.items()}
            )
        
        # Save filled form
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
            
        return output_path
        
    except Exception as e:
        print(f"Error filling 1040 form: {e}")
        return None
    
@app.route('/outputs/<filename>', methods=['GET'])
def serve_output_file(filename):
    try:
        # Only allow access to specific files for security
        if filename != 'filled_1040.pdf':
            return jsonify({'error': 'File not found'}), 404
            
        outputs_dir = os.path.join(BASE_DIR, 'outputs')
        filepath = os.path.join(outputs_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
            
        return send_file(filepath, as_attachment=False)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)