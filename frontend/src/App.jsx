import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import SourceInspector from './components/SourceInspector';
import DocumentUploadModal from './components/DocumentUploadModal';
import { fetchHealth, fetchTechniques, fetchDocuments, sendChatMessage, selectDocument } from './services/api';

export default function App() {
  const [health, setHealth] = useState(null);
  const [techniques, setTechniques] = useState([]);
  const [selectedTechnique, setSelectedTechnique] = useState('simple_rag');
  const [documents, setDocuments] = useState({ active_document: 'No document loaded', available_documents: [] });
  
  // Hyperparameters
  const [topK, setTopK] = useState(3);
  const [chunkSize, setChunkSize] = useState(1000);
  const [chunkOverlap, setChunkOverlap] = useState(200);

  // Chat State
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Source Chunks Inspector State
  const [showSources, setShowSources] = useState(false);
  const [currentChunks, setCurrentChunks] = useState([]);
  const [selectedChunk, setSelectedChunk] = useState(null);

  // Upload Modal State
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  // Initial Load
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [hData, tData, dData] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchTechniques().catch(() => []),
        fetchDocuments().catch(() => ({ active_document: 'Default Document', available_documents: [] })),
      ]);

      setHealth(hData);
      setTechniques(tData);
      if (dData) setDocuments(dData);
    } catch (err) {
      console.error('Error loading initial data:', err);
    }
  };

  const handleSelectDocument = async (docName) => {
    if (documents.active_document === docName) return;
    setIsLoading(true);
    try {
      await selectDocument(docName, chunkSize, chunkOverlap);
      setDocuments((prev) => ({
        ...prev,
        active_document: docName,
      }));
      const systemMsg = {
        id: Date.now(),
        sender: 'bot',
        text: `Switched active document to "${docName}". Ready to answer questions about this document!`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, systemMsg]);
      setCurrentChunks([]);
    } catch (err) {
      const errorMsg = {
        id: Date.now(),
        sender: 'bot',
        text: `Error activating document "${docName}": ${err.message}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (text) => {
    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(text, selectedTechnique, {
        topK,
        chunkSize,
        chunkOverlap,
      });

      const activeTechObj = techniques.find((t) => t.id === selectedTechnique);
      const botMsg = {
        id: Date.now() + 1,
        sender: 'bot',
        text: response.answer,
        technique: activeTechObj ? activeTechObj.name : selectedTechnique,
        chunks: response.retrieved_chunks,
        metrics: response.metrics,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, botMsg]);
      setCurrentChunks(response.retrieved_chunks || []);
      if (response.retrieved_chunks && response.retrieved_chunks.length > 0) {
        setShowSources(true);
      }
    } catch (err) {
      const errorMsg = {
        id: Date.now() + 1,
        sender: 'bot',
        text: `Error processing query: ${err.message}. Please check if the backend REST server is running.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectChunk = (chunk) => {
    setSelectedChunk(chunk);
    setShowSources(true);
  };

  const handleUploadSuccess = (docName) => {
    setDocuments((prev) => ({
      ...prev,
      active_document: docName,
      available_documents: [
        { name: docName, source: 'Uploaded' },
        ...(prev.available_documents || []),
      ],
    }));
    loadInitialData();
  };

  return (
    <div className="app-layout">
      <Header
        activeDoc={documents.active_document}
        onOpenUpload={() => setIsUploadOpen(true)}
        health={health}
        onToggleSources={() => setShowSources(!showSources)}
        showSources={showSources}
        sourcesCount={currentChunks.length}
      />

      <div className="main-content">
        <Sidebar
          techniques={techniques}
          selectedTechnique={selectedTechnique}
          onSelectTechnique={setSelectedTechnique}
          chunkSize={chunkSize}
          setChunkSize={setChunkSize}
          chunkOverlap={chunkOverlap}
          setChunkOverlap={setChunkOverlap}
          topK={topK}
          setTopK={setTopK}
          documents={documents}
          onSelectDocument={handleSelectDocument}
        />

        <ChatWindow
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          activeTechnique={selectedTechnique}
          onSelectChunk={handleSelectChunk}
          onClearHistory={() => {
            setMessages([]);
            setCurrentChunks([]);
          }}
        />

        {showSources && (
          <SourceInspector
            chunks={currentChunks}
            selectedChunk={selectedChunk}
            onClose={() => setShowSources(false)}
          />
        )}
      </div>

      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={handleUploadSuccess}
        chunkSize={chunkSize}
        chunkOverlap={chunkOverlap}
      />
    </div>
  );
}
