import React, { useState, useRef } from 'react';

const API_BASE = 'http://localhost:8000';

function App() {
  const [file, setFile] = useState(null);
  const [subject, setSubject] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('idle'); // 'idle' | 'uploading' | 'success' | 'error'
  const [uploadProgress, setUploadProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [responseData, setResponseData] = useState(null);

  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === 'application/pdf' || droppedFile.name.endsWith('.pdf')) {
        setFile(droppedFile);
        setUploadStatus('idle');
        setResponseData(null);
      } else {
        setUploadStatus('error');
        setStatusMessage('Only PDF files are supported.');
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (selectedFile.type === 'application/pdf' || selectedFile.name.endsWith('.pdf')) {
        setFile(selectedFile);
        setUploadStatus('idle');
        setResponseData(null);
      } else {
        setUploadStatus('error');
        setStatusMessage('Only PDF files are supported.');
      }
    }
  };

  const removeFile = () => {
    setFile(null);
    setUploadStatus('idle');
    setResponseData(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const triggerFileInput = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setUploadStatus('error');
      setStatusMessage('Please select a PDF file to upload.');
      return;
    }
    if (!subject.trim()) {
      setUploadStatus('error');
      setStatusMessage('Please enter a Subject / Category.');
      return;
    }

    setUploadStatus('uploading');
    setUploadProgress(5);
    setStatusMessage('Uploading PDF file...');
    setResponseData(null);

    // Simulate multi-stage progress updates for better UX during synchronous embedding pipeline
    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 95) {
          clearInterval(progressInterval);
          return 95;
        }
        const step = prev < 30 ? 10 : prev < 60 ? 5 : prev < 85 ? 3 : 1;
        return prev + step;
      });
    }, 400);

    const messageTimeout1 = setTimeout(() => {
      setStatusMessage('Analyzing document structure (native vs scanned)...');
    }, 1500);

    const messageTimeout2 = setTimeout(() => {
      setStatusMessage('Extracting document layout and text chunks...');
    }, 4500);

    const messageTimeout3 = setTimeout(() => {
      setStatusMessage('Generating Gemini text embeddings in batches...');
    }, 9000);

    const messageTimeout4 = setTimeout(() => {
      setStatusMessage('Saving embeddings to ChromaDB vector store...');
    }, 15000);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/upload/${encodeURIComponent(subject.trim())}`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);
      clearTimeout(messageTimeout1);
      clearTimeout(messageTimeout2);
      clearTimeout(messageTimeout3);
      clearTimeout(messageTimeout4);

      const data = await response.json();

      if (response.ok) {
        setUploadProgress(100);
        setUploadStatus('success');
        setStatusMessage('Success! PDF ingested, embedded, and indexed successfully.');
        setResponseData(data);
      } else {
        setUploadStatus('error');
        setStatusMessage(data.detail || 'An error occurred during backend ingestion.');
        setResponseData(data);
      }
    } catch (error) {
      clearInterval(progressInterval);
      clearTimeout(messageTimeout1);
      clearTimeout(messageTimeout2);
      clearTimeout(messageTimeout3);
      clearTimeout(messageTimeout4);

      setUploadStatus('error');
      setStatusMessage('Failed to connect to backend server. Please verify it is running on ' + API_BASE);
      setResponseData({ error: 'Connection refused', details: error.message });
    }
  };

  const formatBytes = (bytes, decimals = 2) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  return (
    <div className="admin-card">
      <div className="header">
        <div className="title-container">
          <span className="logo-badge">PREPPILOT</span>
          <h1 className="title">Admin Portal</h1>
        </div>
        <p className="subtitle">Upload study guides & course materials to seed the RAG pipeline</p>
      </div>

      <form onSubmit={handleUpload}>
        {/* PDF Upload Dropzone */}
        {!file ? (
          <div 
            id="upload-dropzone"
            className={`dropzone ${dragActive ? 'drag-active' : ''}`}
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            onClick={triggerFileInput}
          >
            <div className="dropzone-content">
              <svg className="upload-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
              </svg>
              <p className="dropzone-text">Drag & drop your PDF file here, or <span style={{color: '#8b5cf6', textDecoration: 'underline'}}>browse</span></p>
              <p className="dropzone-subtext">Max size: 50MB. Only PDF files are supported.</p>
            </div>
            <input 
              ref={fileInputRef}
              id="file-upload-input"
              type="file" 
              className="file-input" 
              accept="application/pdf"
              onChange={handleFileChange}
            />
          </div>
        ) : (
          <div className="file-card" id="selected-file-card">
            <div className="file-info">
              <svg className="pdf-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
              <div className="file-details">
                <div className="file-name" title={file.name}>{file.name}</div>
                <div className="file-size">{formatBytes(file.size)}</div>
              </div>
            </div>
            <button type="button" id="file-remove-btn" className="remove-btn" onClick={removeFile} title="Remove file">
              <svg style={{width: '20px', height: '20px'}} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* Subject / Category input */}
        <div className="form-group">
          <label htmlFor="subject-input" className="form-label">Subject / Category</label>
          <input 
            type="text" 
            id="subject-input"
            className="form-input" 
            placeholder="e.g. computer-science, cell-biology, history-101"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            disabled={uploadStatus === 'uploading'}
          />
        </div>

        {/* Action button */}
        <button 
          id="upload-submit-btn"
          type="submit" 
          className="submit-btn" 
          disabled={!file || !subject.trim() || uploadStatus === 'uploading'}
        >
          {uploadStatus === 'uploading' ? (
            <>
              <div className="spinner"></div>
              <span>Generating Embeddings...</span>
            </>
          ) : (
            <>
              <svg style={{width: '20px', height: '20px'}} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              <span>Upload & Ingest</span>
            </>
          )}
        </button>
      </form>

      {/* Progress & Message Console */}
      {uploadStatus !== 'idle' && (
        <div className={`status-banner ${uploadStatus === 'uploading' ? 'info' : uploadStatus}`}>
          <div style={{width: '100%'}}>
            <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem'}}>
              {uploadStatus === 'uploading' && (
                <svg className="status-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
              {uploadStatus === 'success' && (
                <svg className="status-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} style={{color: 'var(--success)'}}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
              {uploadStatus === 'error' && (
                <svg className="status-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} style={{color: 'var(--error)'}}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
              <span style={{fontWeight: 500}}>{statusMessage}</span>
            </div>

            {uploadStatus === 'uploading' && (
              <div className="progress-container">
                <div className="progress-bar" style={{width: `${uploadProgress}%`}}></div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* JSON Response Details Inspector */}
      {responseData && (
        <div className="response-container">
          <div className="response-header">
            <span className="response-title">Ingestion Output</span>
            <span style={{
              fontSize: '0.8rem', 
              color: uploadStatus === 'success' ? 'var(--success)' : 'var(--error)',
              fontWeight: 600,
              textTransform: 'uppercase'
            }}>
              {uploadStatus === 'success' ? 'Success metrics' : 'Error details'}
            </span>
          </div>
          
          {uploadStatus === 'success' && responseData.total_embedded !== undefined && (
            <div className="response-metric-grid">
              <div className="metric-card">
                <div className="metric-label">Chunks Embedded</div>
                <div className="metric-value">{responseData.total_embedded}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Chroma Store Status</div>
                <div className="metric-value" style={{color: 'var(--success)', fontSize: '1.1rem', marginTop: '0.3rem'}}>
                  {responseData.stored ? 'Indexed' : 'Pending'}
                </div>
              </div>
            </div>
          )}

          <pre className="response-body">
            {JSON.stringify(responseData, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default App;
