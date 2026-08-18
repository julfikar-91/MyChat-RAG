import React from 'react';
import { User, Bot, Sparkles, Clock, FileText, CheckCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function MessageItem({ message, onSelectChunk }) {
  const isUser = message.sender === 'user';

  return (
    <div className={`message-row ${isUser ? 'user-row' : 'bot-row'} animate-fade-in`}>
      <div className="message-avatar">
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>

      <div className="message-content-wrapper">
        <div className="message-header">
          <span className="sender-name">{isUser ? 'You' : 'MyChat RAG Assistant'}</span>
          {message.technique && (
            <span className="tech-tag">{message.technique}</span>
          )}
          <span className="message-time">{message.timestamp}</span>
        </div>

        <div className="message-body markdown-content">
          {isUser ? (
            <p>{message.text}</p>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.text}
            </ReactMarkdown>
          )}
        </div>

        {/* Retrieved Sources Badges */}
        {message.chunks && message.chunks.length > 0 && (
          <div className="sources-preview">
            <span className="sources-label">
              <FileText size={12} /> Sources ({message.chunks.length}):
            </span>
            <div className="chunks-chips">
              {message.chunks.map((chunk) => (
                <button
                  key={chunk.id}
                  className="chunk-chip"
                  onClick={() => onSelectChunk(chunk)}
                >
                  Chunk #{chunk.id} {chunk.page ? `(p. ${chunk.page})` : ''}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Query Execution Metrics */}
        {message.metrics && (
          <div className="message-metrics">
            <Clock size={12} />
            <span>Total: {message.metrics.total_time_ms}ms</span>
            <span className="metric-divider">•</span>
            <span>Retrieval: {message.metrics.retrieval_time_ms}ms</span>
            <span className="metric-divider">•</span>
            <span>Gen: {message.metrics.generation_time_ms}ms</span>
          </div>
        )}
      </div>
    </div>
  );
}
