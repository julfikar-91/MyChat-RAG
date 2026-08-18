import React from 'react';
import { Bot, FileText, Upload, Activity, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';

export default function Header({ 
  activeDoc, 
  onOpenUpload, 
  health, 
  onToggleSources, 
  showSources,
  sourcesCount 
}) {
  return (
    <header className="glass-panel header-container">
      <div className="header-left">
        <div className="logo-badge">
          <Bot className="logo-icon" />
          <span className="logo-sparkle"><Sparkles size={12} /></span>
        </div>
        <div>
          <h1 className="header-title">MyChat RAG Studio</h1>
          <p className="header-subtitle">Advanced Retrieval-Augmented Generation Interface</p>
        </div>
      </div>

      <div className="header-actions">
        {/* Document Status */}
        <div className="doc-pill" onClick={onOpenUpload} title="Click to upload or switch document">
          <FileText size={16} className="text-indigo" />
          <span className="doc-name">{activeDoc || 'No document selected'}</span>
          <Upload size={14} className="upload-icon" />
        </div>

        {/* Sources Toggle */}
        <button 
          className={`source-toggle-btn ${showSources ? 'active' : ''}`}
          onClick={onToggleSources}
        >
          <Activity size={16} />
          <span>Retrieved Context</span>
          {sourcesCount > 0 && <span className="sources-count">{sourcesCount}</span>}
        </button>

        {/* Backend Health Status */}
        <div className={`health-badge ${health?.status === 'healthy' ? 'online' : 'offline'}`}>
          {health?.status === 'healthy' ? (
            <>
              <CheckCircle2 size={14} />
              <span>REST API Connected</span>
            </>
          ) : (
            <>
              <AlertCircle size={14} />
              <span>Connecting...</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
