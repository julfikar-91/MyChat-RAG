import React, { useState } from 'react';
import { Upload, X, FileText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { uploadDocument } from '../services/api';

export default function DocumentUploadModal({ isOpen, onClose, onUploadSuccess, chunkSize, chunkOverlap }) {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  if (!isOpen) return null;

  const handleFileDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    setError(null);
    try {
      const res = await uploadDocument(file, chunkSize, chunkOverlap);
      onUploadSuccess(res.document_name);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to upload document');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="glass-panel modal-content animate-fade-in">
        <div className="modal-header">
          <h2>Upload PDF Document</h2>
          <button className="close-btn" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="modal-body">
          <div 
            className={`dropzone ${dragOver ? 'dragover' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleFileDrop}
          >
            <input 
              type="file" 
              accept=".pdf,.txt"
              id="file-input" 
              onChange={(e) => setFile(e.target.files[0])}
              style={{ display: 'none' }}
            />
            <label htmlFor="file-input" className="dropzone-label">
              {file ? (
                <div className="selected-file-info">
                  <FileText size={36} className="text-indigo" />
                  <span className="file-name">{file.name}</span>
                  <span className="file-size">{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
                </div>
              ) : (
                <>
                  <Upload size={36} className="text-muted" />
                  <p>Drag and drop your PDF / TXT document here</p>
                  <span className="browse-text">or click to browse files</span>
                </>
              )}
            </label>
          </div>

          {error && (
            <div className="error-alert">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div className="modal-footer">
            <button className="cancel-btn" onClick={onClose} disabled={isUploading}>Cancel</button>
            <button 
              className="submit-btn" 
              onClick={handleUpload}
              disabled={!file || isUploading}
            >
              {isUploading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Processing & Indexing...
                </>
              ) : (
                'Index Document'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
