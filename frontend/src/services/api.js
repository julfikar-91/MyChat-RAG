const API_BASE = import.meta.env.VITE_API_BASE_URL
  ? import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '')
  : '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchTechniques() {
  const res = await fetch(`${API_BASE}/techniques`);
  if (!res.ok) throw new Error('Failed to fetch RAG techniques');
  return res.json();
}

export async function fetchDocuments() {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function uploadDocument(file, chunkSize = 1000, chunkOverlap = 200) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('chunk_size', chunkSize);
  formData.append('chunk_overlap', chunkOverlap);

  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Document upload failed');
  }
  return res.json();
}

export async function selectDocument(filename, chunkSize = 1000, chunkOverlap = 200) {
  const res = await fetch(`${API_BASE}/documents/select`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      filename,
      chunk_size: chunkSize,
      chunk_overlap: chunkOverlap,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to activate document');
  }
  return res.json();
}

export async function sendChatMessage(query, technique = 'simple_rag', options = {}) {
  const payload = {
    query,
    technique,
    chunk_size: options.chunkSize || 1000,
    chunk_overlap: options.chunkOverlap || 200,
    top_k: options.topK || 3,
  };

  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Chat query failed');
  }

  return res.json();
}
