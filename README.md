# AI-Tax-Return-Agent

## Goals
The goal of this project is to develop a functional tax assistant prototype that automates personal tax filing. The system will process standard tax documents, calculate tax liability, and generate a completed IRS Form 1040. By streamlining tax filing through automation, the solution aims to reduce errors and save users time compared to manual preparation methods. The prototype will demonstrate core capabilities in document ingestion, data extraction, and tax form generation while maintaining accuracy and compliance with IRS regulations.

## Flow

#### Upload
<p align="center">
  <img width="350" height="350" alt="Image" src="https://github.com/user-attachments/assets/b77b9ab3-4177-4a9e-b1d2-5fe129eb6b70" />
</p>

When users first visit the website, they're prompted to enter their basic tax information, including filing status, number of dependent children, and other dependents. This essential information establishes the framework for all subsequent tax calculations and determines eligibility for various deductions and credits. The system requires these details upfront to ensure accurate processing later in the workflow.<br \> <br \>

<p align="center">
  <img width="350" height="350" alt="Image" src="https://github.com/user-attachments/assets/ab3dce08-0d8e-4e1b-982a-e5e16d72d344" />
</p>

After completing their profile, users can upload their tax documents by selecting the appropriate W-2, 1099-NEC, or 1099-INT forms through an intuitive file selection interface. The application prevents submission until both a valid filing status has been selected and at least one qualifying tax document has been chosen. This validation step helps maintain data integrity and prevents processing errors down the line.

The collected filing status and dependent information play several crucial roles in the tax preparation process. It directly influences the standard deduction amount applied to the user's taxable income and determines which tax brackets will be used for calculations. Additionally, this information affects eligibility for child tax credits and other dependent-related benefits, while also guiding the system in properly interpreting and processing the uploaded documents.

#### Parse
<p align="center">
<img width="350" height="450" alt="Image" src="https://github.com/user-attachments/assets/bb4485f2-2b8b-4cd8-ba76-7b90cd1cf0e1" />
</p>

When documents are uploaded, they're stored in a temporary "uploads" directory while processing begins. The system employs a hybrid extraction approach to handle all document types efficiently. For digital PDFs with embedded text layers, it uses PDFplumber for fast, accurate text extraction. For scanned documents or image-based files, it automatically switches to pytesseract's OCR technology to reliably convert images to machine-readable text.

After extraction, the system classifies each document by analyzing its content structure and key identifiers. It looks for distinctive patterns like "Form W-2" headers or "Nonemployee Compensation" labels to determine whether it's processing a W-2, 1099-NEC, or 1099-INT form. Each classified document then routes to its specialized parser - W-2 forms are scanned for wages and federal tax withheld, 1099-NEC for nonemployee compensation amounts, and 1099-INT for interest income figures.

The system maintains strict data hygiene throughout this process. It automatically detects and skips duplicate uploads to prevent redundant processing. Documents that don't match the supported form types are immediately discarded without any data extraction. Similarly, files missing required values or containing unreadable content generate clear error messages rather than incomplete or inaccurate data. Only successfully parsed values from valid forms are stored in the system's secure memory for the calculation phase.

#### Calculate
<p align="center">
  <img width="350" height="225" alt="Image" src="https://github.com/user-attachments/assets/218d2b46-a854-41e8-937c-0cef7438a1bd" />
</p>

The tax calculation process begins when the user clicks the "Calculate Tax" button. First, the system aggregates all income sources: wages from W-2 forms, nonemployee compensation from 1099-NEC forms, and interest income from 1099-INT forms. These values are summed to determine the total gross income. Next, the applicable standard deduction is automatically applied based on the user's filing status.

The system then calculates the taxable income by subtracting the standard deduction from the total gross income. Using the 2024 IRS tax brackets, it performs a progressive tax calculation where different portions of the taxable income are taxed at increasing rates (from 10% to 37%). The specific brackets used vary significantly depending on filing status.

Before finalizing the tax amount, the system applies relevant credits. Each qualifying child reduces the tax by $2,000 (Child Tax Credit), while other dependents qualify for a $500 credit. These credits phase out for higher incomes - for every $1,000 that the adjusted gross income exceeds the threshold (which varies by filing status), the total credit is reduced by $50. The final tax liability is determined by subtracting these credits from the initial tax calculation.

Finally, the system compares the calculated tax liability against the total federal tax withheld (as reported on W-2 forms). If more was withheld than owed, the result is a refund; if less was withheld, the user owes additional payment. Throughout this process, the system validates all inputs, handles edge cases like negative values, and ensures mathematical precision down to the cent.

#### Generate Form
<p>
  The system automatically generates a completed IRS Form 1040 simultaneously with the tax calculations. Using PyPDF2's advanced PDF manipulation capabilities, it precisely maps all calculated values to their corresponding fields on the digital 1040 template. 
<br \> <br \>
</p>

<p align="center">
  <img width="450" height="450" alt="Image" src="https://github.com/user-attachments/assets/c5dab317-4bc5-400d-b78f-e3cedf824af2" />
</p>

Once generated, users can immediately access their completed tax form through multiple convenient options. Clicking "Preview" opens an integrated PDF viewer that displays the filled 1040 form, allowing for careful review before submission. The download functionality provides a pristine copy of the finalized form when the user clicks either the main "Download" button or the download option in the preview window.

## Chatbot
![Image](https://github.com/user-attachments/assets/f2f99ae6-dfb7-4a96-ba72-f8a19be6afbd)

The application features an AI-powered tax assistant chatbot that provides real-time answers to US tax-related questions. When the floating button in the bottom-right corner of the interface is clicked, the chat window expands out. Using OpenAI's GPT-3.5-turbo model with a specialized tax prompt, it offers accurate responses about W-2s, 1099 forms, deductions, and 2024 tax rules while politely declining non-tax questions. The chat maintains context by keeping the last three messages in the conversation history and displays messages in distinct visual styles for user queries and bot responses. The interface includes a loading indicator during AI processing and automatically scrolls to show new messages, with robust error handling for network issues. Users can type questions in the input field and submit them either by pressing Enter or clicking the send button.

## Mobile-Friendly
The application features a responsive vertical layout optimized for mobile devices, with all form fields and controls arranged in a single-column flow that adapts seamlessly to smaller screens. The clean, uncluttered interface ensures effortless navigation through touch interactions, while form elements are sized appropriately for finger taps. Despite the compact mobile view, users retain full access to the tax assistant through a persistent floating action button positioned in the bottom-right corner.
<p align="center">
  <img width="300" height="675" alt="Image" src="https://github.com/user-attachments/assets/000d2174-fa8a-4b80-8d81-181e4a1b79a7" />
  <img width="300" height="675" alt="Image" src="https://github.com/user-attachments/assets/b367566b-2708-40b7-ac9f-f2cbbb021f6f" />
</p>

## Reflections



