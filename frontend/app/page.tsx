"use client";

import { useState, ChangeEvent, FormEvent, useEffect } from 'react';
import Head from 'next/head';

type PersonalInfo = {
  filingStatus: string;
  dependentChildren: number;
  otherDependents: number;
};

type UploadedFile = {
  name: string;
  size: number;
  upload_time: number;
  status?: string;
  message?: string;
};

export default function TaxReturnUpload() {
  const [files, setFiles] = useState<File[]>([]);
  const [uploadStatus, setUploadStatus] = useState('');
  const [personalInfo, setPersonalInfo] = useState<PersonalInfo>({
    filingStatus: '',
    dependentChildren: 0,
    otherDependents: 0
  });
  const [dependentChildrenInput, setDependentChildrenInput] = useState('0');
  const [otherDependentsInput, setOtherDependentsInput] = useState('0');
  const isProcessingDisabled = !personalInfo.filingStatus || files.length === 0;
  const [taxResults, setTaxResults] = useState<any>(null);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  
  // Reset state on page refresh
useEffect(() => {
    // Reset frontend state
    setFiles([]);
    setTaxResults(null);
    setUploadedFiles([]);
    
    // Clear backend uploads folder and reset data store
    const resetEverything = async () => {
      try {
        await fetch('http://localhost:5000/clear-uploads', {
          method: 'POST'
        });
      } catch (error) {
        console.error('Error resetting:', error);
      }
    };
    resetEverything();
}, []);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handlePersonalInfoChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const { name, value } = e.target;
    setPersonalInfo(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleDependentChildrenChange = (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setDependentChildrenInput(value);
    setPersonalInfo(prev => ({
      ...prev,
      dependentChildren: value === '' ? 0 : parseInt(value) || 0
    }));
  };

  const handleOtherDependentsChange = (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setOtherDependentsInput(value);
    setPersonalInfo(prev => ({
      ...prev,
      otherDependents: value === '' ? 0 : parseInt(value) || 0
    }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    
    if (files.length === 0) {
      setUploadStatus('Please select at least one file');
      return;
    }

    try {
      setUploadStatus('Uploading files and submitting personal information...');
      
      // First submit personal info
      const personalInfoResponse = await fetch('http://localhost:5000/submit-personal-info', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filingStatus: personalInfo.filingStatus,
          dependentChildren: personalInfo.dependentChildren,
          otherDependents: personalInfo.otherDependents
        }),
      });

      if (!personalInfoResponse.ok) {
        throw new Error('Failed to submit personal information');
      }

      // Then upload files
      const formData = new FormData();
      files.forEach(file => formData.append('files', file));

      const filesResponse = await fetch('http://localhost:5000/upload', {
        method: 'POST',
        body: formData,
      });

      if (!filesResponse.ok) {
        throw new Error(`Server responded with status ${filesResponse.status}`);
      }

      const data = await filesResponse.json();
      
      // Check for skipped files
      const skippedFiles = data.files.filter((file: any) => file.status === 'skipped');
      const processedFiles = data.files.filter((file: any) => file.status === 'processed');
      
      let statusMessage = '';
      if (processedFiles.length > 0) {
        statusMessage += `${processedFiles.length} file(s) processed successfully. `;
      }
      if (skippedFiles.length > 0) {
        statusMessage += `${skippedFiles.length} file(s) skipped (already uploaded).`;
      }
      
      const errorFiles = data.files.filter((file: any) => file.error);
      if (errorFiles.length > 0) {
        const errorMessages = errorFiles.map((file: any) => file.error).join('\n');
        statusMessage += ` Errors: ${errorMessages}`;
      }
      
      setUploadStatus(statusMessage);
      await fetchUploadedFiles();
      setFiles([]);
      
    } catch (error) {
      console.error('Error:', error);
      setUploadStatus(`Error: ${error instanceof Error ? error.message : 'Failed to process request'}`);
    }
  };

  const handleCalculateTax = async () => {
    try {
      const response = await fetch('http://localhost:5000/calculate-tax');
      if (!response.ok) {
        throw new Error('Failed to calculate tax');
      }
      const data = await response.json();
      setTaxResults(data.results);
    } catch (error) {
      setUploadStatus(`Error calculating tax: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

 const handleResetUploads = async () => {
    try {
      setUploadStatus('Resetting uploads and data...');
      
      // Clear uploads and reset data store
      const response = await fetch('http://localhost:5000/clear-uploads', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) throw new Error('Failed to reset uploads and data');
      
      // Clear all frontend states
      setFiles([]);
      setTaxResults(null);
      setUploadedFiles([]);
      setUploadStatus('All uploads and data have been reset');
    } catch (error) {
      setUploadStatus(`Error resetting: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
};

  const fetchUploadedFiles = async () => {
    try {
      const response = await fetch('http://localhost:5000/get-uploaded-files');
      if (!response.ok) throw new Error('Failed to fetch uploaded files');
      const data = await response.json();
      if (data.success) {
        setUploadedFiles(data.files);
      }
    } catch (error) {
      console.error('Error fetching uploaded files:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <Head>
        <title>AI Tax Return Agent</title>
      </Head>
      
      <div className="max-w-md mx-auto bg-white rounded-xl shadow-md overflow-hidden md:max-w-2xl p-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">AI Tax Return Agent</h1>
        
        {/* Personal Information Section */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-4">Personal Information</h2>
          
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="filingStatus">
              Filing Status
            </label>
            <select
              id="filingStatus"
              name="filingStatus"
              value={personalInfo.filingStatus}
              onChange={handlePersonalInfoChange}
              className="shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              required
            >
              <option value="">Select filing status</option>
              <option value="single">Single</option>
              <option value="married_joint">Married Filing Jointly</option>
              <option value="married_separate">Married Filing Separately</option>
              <option value="head_of_household">Head of Household</option>
              <option value="widow">Qualifying Widow</option>
            </select>
          </div>
          
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="dependentChildren">
              Number of Dependent Children
            </label>
            <input
              type="number"
              id="dependentChildren"
              name="dependentChildren"
              min="0"
              value={dependentChildrenInput}
              onChange={handleDependentChildrenChange}
              onFocus={(e) => {
                if (e.target.value === '0') {
                  setDependentChildrenInput('');
                }
              }}
              onBlur={(e) => {
                if (e.target.value === '') {
                  setDependentChildrenInput('0');
                }
              }}
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              required
            />
          </div>

          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="otherDependents">
              Number of Other Dependents
            </label>
            <input
              type="number"
              id="otherDependents"
              name="otherDependents"
              min="0"
              value={otherDependentsInput}
              onChange={handleOtherDependentsChange}
              onFocus={(e) => {
                if (e.target.value === '0') {
                  setOtherDependentsInput('');
                }
              }}
              onBlur={(e) => {
                if (e.target.value === '') {
                  setOtherDependentsInput('0');
                }
              }}
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              required
            />
          </div>
        </div>
        
        {/* File Upload Form */}
        <form onSubmit={handleSubmit}>
          <h2 className="text-lg font-semibold mb-4">Upload Tax Documents</h2>
          <p className="text-sm text-gray-600 mb-4">
            Supported documents: W-2, 1099-INT, 1099-NEC (PDF format)
          </p>
          
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="files">
              Select Files
            </label>
            <input
              type="file"
              id="files"
              name="files"
              onChange={handleFileChange}
              className="block w-full text-sm text-transparent
                file:mr-4 file:py-2 file:px-4
                file:rounded-md file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100"
              multiple
              accept=".pdf"
              key={files.length}
            />

            {files.length > 0 && (
              <div className="mt-2 text-sm text-gray-600">
                Selected: {files.length} file(s)
                <ul className="list-disc pl-5 mt-1">
                  {files.map((file, index) => (
                    <li key={index}>{file.name}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          
          <div className="flex flex-col space-y-4">
            <div className="flex space-x-4">
              <button
                type="submit"
                disabled={isProcessingDisabled}
                className={`${
                  isProcessingDisabled
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-green-500 hover:bg-green-700'
                } text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline flex-1`}
              >
                Upload and Process Files
              </button>
              
              <button
                type="button"
                onClick={handleCalculateTax}
                disabled={!uploadedFiles.length}
                className={`${
                  !uploadedFiles.length
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-500 hover:bg-blue-700'
                } text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline flex-1`}
              >
                Calculate Tax
              </button>
            </div>

            {isProcessingDisabled && personalInfo.filingStatus === '' && (
              <p className="text-xs text-red-500">
                Please select a filing status first
              </p>
            )}
            {isProcessingDisabled && files.length === 0 && (
              <p className="text-xs text-red-500">
                Please select at least one file to upload
              </p>
            )}
          </div>
        </form>
        
        {/* Status and Results */}
        {uploadStatus && (
          <div className={`mt-4 p-3 rounded ${
            uploadStatus.includes('Error') || 
            uploadStatus.includes('Please upload a W-2, 1099-NEC, or a 1099-INT form')
              ? 'bg-red-100 text-red-700' 
              : 'bg-blue-100 text-blue-700'
          }`}>
            {uploadStatus}
          </div>
        )}

        {uploadedFiles.length > 0 && (
          <div className="mt-6">
            <h3 className="text-md font-semibold mb-2">Uploaded Files:</h3>
            <ul className="space-y-2">
              {uploadedFiles.map((file, index) => (
                <li key={index} className={`p-3 rounded ${file.status === 'skipped' ? 'bg-yellow-100' : 'bg-gray-100'}`}>
                  <p><strong>Filename:</strong> {file.name}</p>
                  {file.status === 'skipped' && (
                    <p className="text-yellow-700 text-sm">Already uploaded - skipped</p>
                  )}
                  <p className="text-sm text-gray-600">
                    Size: {(file.size / 1024).toFixed(2)} KB • 
                    Uploaded: {new Date(file.upload_time * 1000).toLocaleString()}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Reset Uploads Button */}
        {uploadStatus && uploadStatus.includes('successfully') && (
          <div className="mt-4">
            <button
              onClick={handleResetUploads}
              className="bg-yellow-500 hover:bg-yellow-600 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
            >
              Reset All Uploads
            </button>
          </div>
        )}

        {taxResults && (
          <div className="mt-6 p-4 bg-green-50 rounded-lg">
            <h3 className="text-lg font-semibold mb-2">Tax Calculation Results</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="font-medium">Total Income:</p>
                <p>${taxResults.total_income.toFixed(2)}</p>
              </div>
              <div>
                <p className="font-medium">Tax Owed:</p>
                <p>${taxResults.tax_owed.toFixed(2)}</p>
              </div>
              <div>
                <p className="font-medium">Federal Tax Withheld:</p>
                <p>${taxResults.federal_withheld.toFixed(2)}</p>
              </div>
              <div>
                <p className="font-medium">Refund/Amount Due:</p>
                <p className={taxResults.refund_or_due >= 0 ? 'text-green-600' : 'text-red-600'}>
                  ${Math.abs(taxResults.refund_or_due).toFixed(2)} 
                  {taxResults.refund_or_due >= 0 ? ' Refund' : ' Due'}
                </p>
              </div>
              <div>
                <p className="font-medium">Credits Applied:</p>
                <p>${taxResults.credits_applied.toFixed(2)}</p>
              </div>
            </div>
            <div className="mt-4">
              <h4 className="font-medium mb-1">Income Breakdown:</h4>
              <ul className="text-sm">
                <li>Wages: ${taxResults.breakdown.wages.toFixed(2)}</li>
                <li>1099-NEC Income: ${taxResults.breakdown.nec_income.toFixed(2)}</li>
                <li>1099-INT Income: ${taxResults.breakdown.interest_income.toFixed(2)}</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}