"use client";

import { useState, ChangeEvent, FormEvent } from 'react';
import Head from 'next/head';

type PersonalInfo = {
  filingStatus: string;
  dependents: number;
};

type FileResult = {
  filename: string;
  text: string;
  message: string;
};

export default function TaxReturnUpload() {
  const [files, setFiles] = useState<File[]>([]);
  const [uploadStatus, setUploadStatus] = useState('');
  const [personalInfo, setPersonalInfo] = useState<PersonalInfo>({
    filingStatus: '',
    dependents: 0  // Numeric value in state
  });
  const [dependentsInput, setDependentsInput] = useState('0');  // Display value
  const [results, setResults] = useState<FileResult[] | null>(null);
  const isProcessingDisabled = !personalInfo.filingStatus || files.length === 0;

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
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

  const handleDependentsChange = (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setDependentsInput(value);
    setPersonalInfo(prev => ({
      ...prev,
      dependents: value === '' ? 0 : parseInt(value) || 0
    }));
  };

const handleSubmitFiles = async (e: FormEvent) => {
  e.preventDefault();
  
  if (files.length === 0) {
    setUploadStatus('Please select at least one file');
    return;
  }

  try {
    setUploadStatus('Uploading files...');
    
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    const response = await fetch('http://localhost:5000/upload', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Server responded with status ${response.status}`);
    }

    const data = await response.json();
    
    // Check for errors in processed files
    const errorFiles = data.files.filter((file: any) => file.error);
    if (errorFiles.length > 0) {
      // Join all error messages without "undefined"
      const errorMessages = errorFiles.map((file: any) => file.error).join('\n');
      setUploadStatus(errorMessages);
    } else {
      setResults(data.files.map((file: any) => ({
        filename: file.original_name,
        message: `Saved as ${file.saved_name}`,
        text: file.extracted_text || 'File processed successfully'
      })));
      setUploadStatus('Files uploaded successfully!');
    }
    
  } catch (error) {
    console.error('Upload error:', error);
    setUploadStatus(`Error: ${error instanceof Error ? error.message : 'Failed to upload files'}`);
  }
};

  const handleSubmitPersonalInfo = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch('http://localhost:5000/submit-personal-info', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(personalInfo),
      });

      const data = await response.json();
      if (response.ok) {
        setUploadStatus('Personal information submitted successfully!');
      } else {
        setUploadStatus(`Error: ${data.error}`);
      }
    } catch (error) {
      setUploadStatus(`Error: ${(error as Error).message}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <Head>
        <title>AI Tax Return Agent</title>
      </Head>
      
      <div className="max-w-md mx-auto bg-white rounded-xl shadow-md overflow-hidden md:max-w-2xl p-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">AI Tax Return Agent</h1>
        
        {/* Personal Information Form */}
        <form onSubmit={handleSubmitPersonalInfo} className="mb-8">
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
            <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="dependents">
              Number of Dependents
            </label>
            <input
              type="number"
              id="dependents"
              name="dependents"
              min="0"
              value={dependentsInput}
              onChange={handleDependentsChange}
              onFocus={(e) => {
                if (e.target.value === '0') {
                  setDependentsInput('');
                }
              }}
              onBlur={(e) => {
                if (e.target.value === '') {
                  setDependentsInput('0');
                }
              }}
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              required
            />
          </div>
          
          <button
            type="submit"
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
          >
            Save Personal Info
          </button>
        </form>
        
        {/* File Upload Form */}
        <form onSubmit={handleSubmitFiles}>
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
              className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-md file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100"
              multiple
              accept=".pdf"
            />
          </div>
          
          <button
            type="submit"
            disabled={isProcessingDisabled}
            className={`${
              isProcessingDisabled
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-green-500 hover:bg-green-700'
            } text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline`}
          >
            Upload and Process Files
          </button>
          {isProcessingDisabled && personalInfo.filingStatus === '' && (
            <p className="text-xs text-red-500 mt-1">
              Please select a filing status first
            </p>
          )}
          {isProcessingDisabled && files.length === 0 && (
            <p className="text-xs text-red-500 mt-1">
              Please select at least one file to upload
            </p>
          )}
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
        
        {results && (
          <div className="mt-6">
            <h3 className="text-md font-semibold mb-2">Processed Files:</h3>
            <ul className="space-y-2">
              {results.map((result, index) => (
                <li key={index} className="p-3 bg-gray-100 rounded">
                  <p><strong>Filename:</strong> {result.filename}</p>
                  <p><strong>Status:</strong> {result.message}</p>
                  <details className="mt-2">
                    <summary className="text-sm text-blue-600 cursor-pointer">View extracted text</summary>
                    <pre className="text-xs bg-white p-2 mt-1 rounded overflow-auto max-h-40">{result.text}</pre>
                  </details>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}