import React, { useState, useEffect, useRef } from 'react';

const API_BASE = 'http://localhost:8000';

function App() {
  // Navigation tabs: 'subjects' | 'upload'
  const [activeTab, setActiveTab] = useState('subjects');

  // Subjects lists and fetch states
  const [subjects, setSubjects] = useState([]);
  const [loadingSubjects, setLoadingSubjects] = useState(false);

  // New Subject form states
  const [subjectName, setSubjectName] = useState('');
  const [subjectCodeInput, setSubjectCodeInput] = useState('');
  const [universityInput, setUniversityInput] = useState('');
  const [semester, setSemester] = useState('');
  const [subjectActionStatus, setSubjectActionStatus] = useState({ type: '', message: '' }); // 'success' | 'error' | ''
  const [subjectActionLoading, setSubjectActionLoading] = useState(false);

  // Ingestion upload states
  const [selectedSubjectId, setSelectedSubjectId] = useState('');
  const [docType, setDocType] = useState('notes'); // 'notes' | 'pyq'
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('idle'); // 'idle' | 'uploading' | 'success' | 'error'
  const [uploadProgress, setUploadProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [responseData, setResponseData] = useState(null);

  const fileInputRef = useRef(null);

  // Fetch subjects on mount & when returning to subject tab
  useEffect(() => {
    fetchSubjectsList();
  }, []);

  const fetchSubjectsList = async () => {
    setLoadingSubjects(true);
    try {
      const response = await fetch(`${API_BASE}/subjects`);
      const resData = await response.json();
      if (response.ok && resData.success) {
        setSubjects(resData.data || []);
        // Auto-select first subject if not set
        if (resData.data && resData.data.length > 0 && !selectedSubjectId) {
          setSelectedSubjectId(resData.data[0].subject_id.toString());
        }
      }
    } catch (error) {
      console.error('Error fetching subjects:', error);
    } finally {
      setLoadingSubjects(false);
    }
  };

  const handleCreateSubject = async (e) => {
    e.preventDefault();
    if (!subjectName.trim()) {
      setSubjectActionStatus({ type: 'error', message: 'Subject name is required.' });
      return;
    }

    setSubjectActionLoading(true);
    setSubjectActionStatus({ type: '', message: '' });

    // Parse comma-separated fields
    const subject_codes = subjectCodeInput
      .split(',')
      .map((c) => c.trim())
      .filter(Boolean);
    const universities = universityInput
      .split(',')
      .map((u) => u.trim())
      .filter(Boolean);
    const semValue = semester ? parseInt(semester, 10) : null;

    const payload = {
      subject_name: subjectName.trim(),
      subject_codes: subject_codes.length > 0 ? subject_codes : null,
      universities: universities.length > 0 ? universities : null,
      slugs: null,
      semester: semValue,
    };

    try {
      const response = await fetch(`${API_BASE}/subjects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const resData = await response.json();

      if (response.ok && resData.success) {
        setSubjectActionStatus({
          type: 'success',
          message: `Subject "${subjectName}" created successfully!`,
        });
        // Reset form fields
        setSubjectName('');
        setSubjectCodeInput('');
        setUniversityInput('');
        setSemester('');
        // Refresh directory
        fetchSubjectsList();
      } else {
        setSubjectActionStatus({
          type: 'error',
          message: resData.detail || 'Failed to create subject.',
        });
      }
    } catch (error) {
      setSubjectActionStatus({
        type: 'error',
        message: 'Could not connect to the backend server.',
      });
    } finally {
      setSubjectActionLoading(false);
    }
  };

  const handleDeleteSubject = async (subjectId, subjectName) => {
    if (!window.confirm(`Are you sure you want to delete the subject "${subjectName}"? This will delete all associated data.`)) {
      return;
    }

    setSubjectActionStatus({ type: '', message: '' });
    try {
      const response = await fetch(`${API_BASE}/subjects/${subjectId}`, {
        method: 'DELETE',
      });
      const resData = await response.json();

      if (response.ok && resData.success) {
        setSubjectActionStatus({
          type: 'success',
          message: `Subject "${subjectName}" deleted successfully.`,
        });
        // Refresh subjects
        fetchSubjectsList();
        // Reset selected subject if deleted
        if (selectedSubjectId === subjectId.toString()) {
          setSelectedSubjectId('');
        }
      } else {
        setSubjectActionStatus({
          type: 'error',
          message: resData.detail || 'Failed to delete subject.',
        });
      }
    } catch (error) {
      setSubjectActionStatus({
        type: 'error',
        message: 'Error connecting to the backend for deletion.',
      });
    }
  };

  // Drag and drop events for file ingestion
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

  // Trigger Ingestion Process
  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setUploadStatus('error');
      setStatusMessage('Please select a PDF file to upload.');
      return;
    }
    if (!selectedSubjectId) {
      setUploadStatus('error');
      setStatusMessage('Please select a subject to associate with the document.');
      return;
    }

    setUploadStatus('uploading');
    setUploadProgress(10);
    setStatusMessage('Uploading PDF to backend server...');
    setResponseData(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Trigger ingestion task
      const response = await fetch(`${API_BASE}/subjects/${selectedSubjectId}/upload/${docType}`, {
        method: 'POST',
        body: formData,
      });

      const initData = await response.json();

      if (!response.ok) {
        setUploadStatus('error');
        setStatusMessage(initData.detail || 'An error occurred during upload.');
        setResponseData(initData);
        return;
      }

      const taskId = initData.task_id;
      setUploadProgress(20);
      setStatusMessage('Document uploaded. Initializing background embedding pipeline...');

      // Dynamic task status polling loop
      const pollStatus = async () => {
        try {
          const statusRes = await fetch(`${API_BASE}/tasks/${taskId}/status`);
          const statusData = await statusRes.json();

          if (!statusRes.ok) {
            setUploadStatus('error');
            setStatusMessage('Failed to fetch background task status.');
            setResponseData(statusData);
            return;
          }

          const taskInfo = statusData.data || {};
          
          if (taskInfo.status === 'PROCESSING') {
            setUploadProgress(30);
            setStatusMessage('Processing background task on backend...');
          } else if (taskInfo.status === 'EXTRACTING_TEXT') {
            setUploadProgress(45);
            setStatusMessage('Extracting PDF text structures...');
          } else if (taskInfo.status === 'CHUNKING') {
            setUploadProgress(60);
            setStatusMessage('Splitting parsed document into text chunks...');
          } else if (taskInfo.status === 'EMBEDDING') {
            setUploadProgress(80);
            setStatusMessage('Generating batch vector embeddings with Gemini...');
          } else if (taskInfo.status === 'STORING') {
            setUploadProgress(95);
            setStatusMessage('Indexing vector records in VectorDB...');
          } else if (taskInfo.status === 'COMPLETED') {
            setUploadProgress(100);
            setUploadStatus('success');
            setStatusMessage('Success! Ingestion completed. Chunks embedded and stored.');
            setResponseData(taskInfo);
            return; // Stop polling
          } else if (taskInfo.status === 'FAILED') {
            setUploadStatus('error');
            setStatusMessage(taskInfo.error_message || 'Background ingestion process failed.');
            setResponseData(taskInfo);
            return; // Stop polling
          }

          // Next poll scheduler
          setTimeout(pollStatus, 1500);

        } catch (pollError) {
          setUploadStatus('error');
          setStatusMessage('Network error during status polling: ' + pollError.message);
        }
      };

      // Start polling
      setTimeout(pollStatus, 1500);

    } catch (error) {
      setUploadStatus('error');
      setStatusMessage('Failed to establish connection with the backend API.');
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
          <h1 className="title">Admin Dashboard</h1>
        </div>
        <p className="subtitle">Manage courses and ingest learning materials to the RAG pipeline</p>
      </div>

      {/* Tabs Switcher */}
      <div className="tabs-container">
        <button
          className={`tab-btn ${activeTab === 'subjects' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('subjects');
            setSubjectActionStatus({ type: '', message: '' });
          }}
        >
          📂 Subject Directory
        </button>
        <button
          className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('upload');
            fetchSubjectsList(); // Ensure dropdown is up to date
          }}
        >
          📤 Document Ingestion
        </button>
      </div>

      {/* TAB 1: SUBJECT DIRECTORY MANAGEMENT */}
      {activeTab === 'subjects' && (
        <div className="dashboard-layout">
          {/* Create Subject Column */}
          <div>
            <h3 style={{ marginBottom: '1.25rem', color: '#a5b4fc', fontSize: '1.15rem' }}>➕ Create Subject</h3>
            <form onSubmit={handleCreateSubject}>
              <div className="form-group">
                <label className="form-label">Subject Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Operating Systems"
                  value={subjectName}
                  onChange={(e) => setSubjectName(e.target.value)}
                  disabled={subjectActionLoading}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Subject Codes (comma separated)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. CS-401, OS-30"
                  value={subjectCodeInput}
                  onChange={(e) => setSubjectCodeInput(e.target.value)}
                  disabled={subjectActionLoading}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Universities (comma separated)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Stanford, MIT"
                  value={universityInput}
                  onChange={(e) => setUniversityInput(e.target.value)}
                  disabled={subjectActionLoading}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Semester</label>
                <input
                  type="number"
                  min="1"
                  max="12"
                  className="form-input"
                  placeholder="e.g. 5"
                  value={semester}
                  onChange={(e) => setSemester(e.target.value)}
                  disabled={subjectActionLoading}
                />
              </div>

              <button type="submit" className="submit-btn" disabled={subjectActionLoading || !subjectName.trim()}>
                {subjectActionLoading ? <div className="spinner"></div> : 'Create Subject'}
              </button>
            </form>

            {/* Subject Status Message */}
            {subjectActionStatus.message && (
              <div className={`status-banner ${subjectActionStatus.type}`}>
                <span>{subjectActionStatus.message}</span>
              </div>
            )}
          </div>

          {/* Directory Column */}
          <div>
            <h3 style={{ marginBottom: '1.25rem', color: '#a5b4fc', fontSize: '1.15rem' }}>📂 Current Subjects</h3>
            {loadingSubjects ? (
              <div style={{ textAlign: 'center', padding: '2rem' }}>
                <div className="spinner" style={{ margin: '0 auto 1rem' }}></div>
                <p style={{ color: 'var(--text-muted)' }}>Loading subjects directory...</p>
              </div>
            ) : subjects.length > 0 ? (
              <div className="subjects-list">
                {subjects.map((sub) => (
                  <div key={sub.subject_id} className="subject-item-card">
                    <div className="subject-card-details">
                      <div className="subject-card-name" title={sub.subject_name}>
                        {sub.subject_name}
                      </div>
                      <div className="badges-container">
                        {sub.semester && (
                          <span className="badge-tag badge-sem">Sem {sub.semester}</span>
                        )}
                        {sub.subject_codes && sub.subject_codes.map((code, idx) => (
                          <span key={idx} className="badge-tag badge-code">{code}</span>
                        ))}
                        {sub.universities && sub.universities.map((uni, idx) => (
                          <span key={idx} className="badge-tag badge-uni">{uni}</span>
                        ))}
                      </div>
                    </div>
                    <button
                      className="remove-btn"
                      onClick={() => handleDeleteSubject(sub.subject_id, sub.subject_name)}
                      title="Delete Subject"
                    >
                      <svg style={{ width: '18px', height: '18px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '3rem 1rem', background: 'rgba(255,255,255,0.01)', border: '1px dashed var(--border-color)', borderRadius: '12px' }}>
                <p style={{ color: 'var(--text-muted)' }}>No subjects found. Create your first subject using the form.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: DOCUMENT INGESTION */}
      {activeTab === 'upload' && (
        <form onSubmit={handleUpload}>
          <div className="form-group">
            <label className="form-label">Associate with Subject</label>
            {subjects.length > 0 ? (
              <select
                className="form-input"
                style={{ background: '#0e131f' }}
                value={selectedSubjectId}
                onChange={(e) => setSelectedSubjectId(e.target.value)}
                disabled={uploadStatus === 'uploading'}
              >
                {subjects.map((sub) => (
                  <option key={sub.subject_id} value={sub.subject_id}>
                    {sub.subject_name} {sub.subject_codes ? `(${sub.subject_codes[0]})` : ''}
                  </option>
                ))}
              </select>
            ) : (
              <div style={{ padding: '0.85rem 1rem', background: 'var(--error-bg)', border: '1px solid var(--error-border)', borderRadius: '10px', color: '#fca5a5', fontSize: '0.95rem' }}>
                ⚠️ No subjects available. Please create a subject in the <b>Subject Directory</b> first.
              </div>
            )}
          </div>

          <div className="form-group">
            <label className="form-label">Document Category</label>
            <div className="doc-type-selector">
              <button
                type="button"
                className={`doc-type-btn ${docType === 'notes' ? 'selected' : ''}`}
                onClick={() => setDocType('notes')}
                disabled={uploadStatus === 'uploading'}
              >
                📝 Lecture Notes / Guide
              </button>
              <button
                type="button"
                className={`doc-type-btn ${docType === 'pyq' ? 'selected' : ''}`}
                onClick={() => setDocType('pyq')}
                disabled={uploadStatus === 'uploading'}
              >
                ❓ Previous Year Q&A (PYQ)
              </button>
            </div>
          </div>

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
                <p className="dropzone-text">Drag & drop subject PDF here, or <span style={{ color: '#8b5cf6', textDecoration: 'underline' }}>browse</span></p>
                <p className="dropzone-subtext">Max allowed size: 50MB. PDFs only.</p>
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
              <button type="button" id="file-remove-btn" className="remove-btn" onClick={removeFile} title="Remove file" disabled={uploadStatus === 'uploading'}>
                <svg style={{ width: '20px', height: '20px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          )}

          {/* Action button */}
          <button
            id="upload-submit-btn"
            type="submit"
            className="submit-btn"
            disabled={!file || !selectedSubjectId || uploadStatus === 'uploading'}
          >
            {uploadStatus === 'uploading' ? (
              <>
                <div className="spinner"></div>
                <span>Ingesting Content...</span>
              </>
            ) : (
              <>
                <svg style={{ width: '20px', height: '20px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                <span>Upload & Ingest to RAG</span>
              </>
            )}
          </button>

          {/* Progress & Status Console */}
          {uploadStatus !== 'idle' && (
            <div className={`status-banner ${uploadStatus === 'uploading' ? 'info' : uploadStatus}`}>
              <div style={{ width: '100%' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                  {uploadStatus === 'uploading' && (
                    <svg className="status-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  )}
                  {uploadStatus === 'success' && (
                    <svg className="status-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} style={{ color: 'var(--success)' }}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  )}
                  {uploadStatus === 'error' && (
                    <svg className="status-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} style={{ color: 'var(--error)' }}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  )}
                  <span style={{ fontWeight: 500 }}>{statusMessage}</span>
                </div>

                {uploadStatus === 'uploading' && (
                  <div className="progress-container">
                    <div className="progress-bar" style={{ width: `${uploadProgress}%` }}></div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* JSON Ingestion Report */}
          {responseData && (
            <div className="response-container">
              <div className="response-header">
                <span className="response-title">Ingestion Output Report</span>
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
                    <div className="metric-label">ChromaDB Status</div>
                    <div className="metric-value" style={{ color: 'var(--success)', fontSize: '1.1rem', marginTop: '0.3rem' }}>
                      {responseData.stored === 1 || responseData.stored === true ? 'Indexed' : 'Pending'}
                    </div>
                  </div>
                </div>
              )}

              <pre className="response-body">
                {JSON.stringify(responseData, null, 2)}
              </pre>
            </div>
          )}
        </form>
      )}
    </div>
  );
}

export default App;
