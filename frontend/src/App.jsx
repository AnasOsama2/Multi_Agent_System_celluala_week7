import React, { useState } from 'react';
import Navbar from './components/Navbar';
import ChatView from './components/ChatView';
import IngestView from './components/IngestView';
import DatasetsView from './components/DatasetsView';
import LogsView from './components/LogsView';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');

  return (
    <div className="app-container">
      {/* Top Navigation Bar with System Telemetry */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Workspace Area */}
      <main className="main-content">
        {activeTab === 'chat' && <ChatView />}
        {activeTab === 'ingest' && <IngestView />}
        {activeTab === 'datasets' && <DatasetsView />}
        {activeTab === 'logs' && <LogsView />}
      </main>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid var(--border-subtle)',
        padding: '1.25rem 2rem',
        textAlign: 'center',
        fontSize: '0.85rem',
        color: 'var(--text-dim)',
        marginTop: 'auto',
        background: 'rgba(10, 13, 20, 0.6)'
      }}>
        <div style={{ maxWidth: '1440px', margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            Multi-Agent RAG System &bull; Collaborative Pipeline (Retriever + Analyst + Answer)
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
            Groq Qwen-3.8-27B &bull; BAAI/bge-reranker-v2-m3 &bull; BAAI/bge-m3
          </div>
        </div>
      </footer>
    </div>
  );
}
