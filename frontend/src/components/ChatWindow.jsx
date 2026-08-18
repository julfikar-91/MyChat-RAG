import React, { useState, useRef, useEffect } from 'react';
import MessageItem from './MessageItem';
import { Send, Sparkles, Loader2, RefreshCw } from 'lucide-react';

export default function ChatWindow({ 
  messages, 
  onSendMessage, 
  isLoading, 
  activeTechnique,
  onSelectChunk,
  onClearHistory
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input);
    setInput('');
  };

  return (
    <main className="glass-panel chat-container">
      {/* Messages Scroll Area */}
      <div className="messages-viewport">
        {messages.length === 0 ? (
          <div className="empty-chat">
            <div className="hero-icon">
              <Sparkles size={36} className="text-indigo" />
            </div>
            <h2>Ask anything about your document</h2>
            <p>Select a RAG technique from the sidebar, upload a PDF, and experience enhanced context retrieval & generation.</p>

            <div className="prompt-suggestions">
              <button onClick={() => setInput('What is the main topic of this document?')}>
                "What is the main topic of this document?"
              </button>
              <button onClick={() => setInput('Summarize the key findings in 3 bullet points.')}>
                "Summarize the key findings in 3 bullet points."
              </button>
              <button onClick={() => setInput('Explain how RAG retrieval is implemented.')}>
                "Explain how RAG retrieval is implemented."
              </button>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageItem 
              key={msg.id} 
              message={msg} 
              onSelectChunk={onSelectChunk}
            />
          ))
        )}

        {isLoading && (
          <div className="message-row bot-row loading-row">
            <div className="message-avatar">
              <Sparkles size={18} className="animate-spin text-indigo" />
            </div>
            <div className="loading-bubbles">
              <span>Running {activeTechnique} retrieval & generating answer...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="chat-input-wrapper">
        <form onSubmit={handleSubmit} className="chat-form">
          <input
            type="text"
            placeholder={`Ask a question using ${activeTechnique}...`}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            className="chat-input"
          />
          <button 
            type="submit" 
            disabled={!input.trim() || isLoading}
            className="send-button"
          >
            {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
          </button>
        </form>
        <div className="input-footer">
          <span>Powered by Gemini & LangChain RAG Engines</span>
          {messages.length > 0 && (
            <button className="clear-btn" onClick={onClearHistory}>
              <RefreshCw size={12} /> Clear Chat
            </button>
          )}
        </div>
      </div>
    </main>
  );
}
