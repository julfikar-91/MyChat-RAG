import React from 'react';
import { X, FileText, CheckCircle2, Bookmark, ExternalLink } from 'lucide-react';

export default function SourceInspector({ chunks, selectedChunk, onClose }) {
  return (
    <aside className="glass-panel source-inspector">
      <div className="inspector-header">
        <div className="header-title-group">
          <FileText size={18} className="text-cyan" />
          <h2>Retrieved Context Inspector</h2>
        </div>
        <button className="close-btn" onClick={onClose}>
          <X size={18} />
        </button>
      </div>

      <div className="inspector-body">
        {chunks.length === 0 ? (
          <div className="empty-inspector">
            <Bookmark size={32} className="text-dim" />
            <p>No retrieved chunks yet. Send a message to inspect RAG context sources.</p>
          </div>
        ) : (
          chunks.map((chunk) => {
            const isSelected = selectedChunk?.id === chunk.id;
            return (
              <div 
                key={chunk.id} 
                className={`source-card ${isSelected ? 'selected' : ''}`}
              >
                <div className="card-top">
                  <span className="chunk-badge">Chunk #{chunk.id}</span>
                  {chunk.page && (
                    <span className="page-tag">Page {chunk.page}</span>
                  )}
                  {chunk.score && (
                    <span className="score-tag">Score: {chunk.score}</span>
                  )}
                </div>

                <div className="card-text">
                  {chunk.content}
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
