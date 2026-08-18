import React from 'react';
import { Cpu, Layers, Sliders, FileCheck, Zap, Info } from 'lucide-react';

export default function Sidebar({
  techniques,
  selectedTechnique,
  onSelectTechnique,
  chunkSize,
  setChunkSize,
  chunkOverlap,
  setChunkOverlap,
  topK,
  setTopK,
  documents,
  onSelectDocument
}) {
  return (
    <aside className="glass-panel sidebar-container">
      <div className="sidebar-section">
        <div className="section-header">
          <Layers size={18} className="text-indigo" />
          <h2>RAG Techniques</h2>
        </div>

        <div className="techniques-list">
          {techniques.map((tech) => {
            const isSelected = selectedTechnique === tech.id;
            return (
              <div
                key={tech.id}
                className={`technique-card ${isSelected ? 'selected' : ''}`}
                onClick={() => onSelectTechnique(tech.id)}
              >
                <div className="tech-card-header">
                  <span className="tech-name">{tech.name}</span>
                  <span className={`tech-badge ${tech.badge.toLowerCase()}`}>{tech.badge}</span>
                </div>
                <p className="tech-desc">{tech.description}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Hyperparameters Configuration */}
      <div className="sidebar-section">
        <div className="section-header">
          <Sliders size={18} className="text-cyan" />
          <h2>Hyperparameters</h2>
        </div>

        <div className="slider-group">
          <div className="slider-label">
            <span>Top-K Chunks</span>
            <span className="slider-value">{topK}</span>
          </div>
          <input
            type="range"
            min="1"
            max="10"
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            className="custom-range"
          />
        </div>

        <div className="slider-group">
          <div className="slider-label">
            <span>Chunk Size (chars)</span>
            <span className="slider-value">{chunkSize}</span>
          </div>
          <input
            type="range"
            min="200"
            max="2000"
            step="100"
            value={chunkSize}
            onChange={(e) => setChunkSize(Number(e.target.value))}
            className="custom-range"
          />
        </div>

        <div className="slider-group">
          <div className="slider-label">
            <span>Chunk Overlap</span>
            <span className="slider-value">{chunkOverlap}</span>
          </div>
          <input
            type="range"
            min="0"
            max="400"
            step="20"
            value={chunkOverlap}
            onChange={(e) => setChunkOverlap(Number(e.target.value))}
            className="custom-range"
          />
        </div>
      </div>

      {/* Loaded Documents */}
      <div className="sidebar-section docs-section">
        <div className="section-header">
          <FileCheck size={18} className="text-purple" />
          <h2>Available Knowledge</h2>
        </div>
        <div className="docs-list">
          {documents?.available_documents?.map((doc, i) => {
            const isActive = documents.active_document === doc.name;
            return (
              <div 
                key={i} 
                className={`doc-item ${isActive ? 'active-doc' : ''}`}
                onClick={() => onSelectDocument && onSelectDocument(doc.name)}
                title="Click to activate document for chat"
                style={{ cursor: 'pointer' }}
              >
                <div className="doc-item-main">
                  <span className="doc-item-name">{doc.name}</span>
                  {isActive && <span className="active-badge">Active</span>}
                </div>
                <span className="doc-item-source">{doc.source}</span>
              </div>
            );
          })}
          {(!documents?.available_documents || documents.available_documents.length === 0) && (
            <p className="empty-docs">No documents uploaded yet.</p>
          )}
        </div>
      </div>
    </aside>
  );
}
