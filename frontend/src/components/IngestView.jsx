import React, { useState, useEffect } from 'react';
import { 
  FileUp, 
  CheckCircle2, 
  AlertCircle, 
  Database, 
  FileText, 
  RefreshCw, 
  Layers, 
  Table, 
  Code, 
  Clock, 
  ArrowRight,
  HardDrive
} from 'lucide-react';

export default function IngestView() {
  const [file, setFile] = useState(null);
  const [tableName, setTableName] = useState('');
  const [isStructured, setIsStructured] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [error, setError] = useState(null);

  const [sources, setSources] = useState([]);
  const [loadingSources, setLoadingSources] = useState(false);

  useEffect(() => {
    fetchSources();
  }, []);

  const fetchSources = async () => {
    setLoadingSources(true);
    try {
      const res = await fetch('/api/v1/sources');
      if (res.ok) {
        const data = await res.json();
        setSources(data.sources || []);
      }
    } catch (e) {
      console.warn('Failed to load sources', e);
    } finally {
      setLoadingSources(false);
    }
  };

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setError(null);
      setUploadResult(null);

      // Auto-detect structured format for CSV/XLSX
      const ext = selected.name.split('.').pop().toLowerCase();
      if (ext === 'csv' || ext === 'xlsx' || ext === 'xls') {
        setIsStructured(true);
        const cleanName = selected.name.replace(/\.[^/.]+$/, '').replace(/[^a-zA-Z0-9_]/g, '_').toLowerCase();
        setTableName(cleanName);
      } else {
        setIsStructured(false);
        setTableName('');
      }
    }
  };

  const handleUpload = async () => {
    if (!file || uploading) return;

    setUploading(true);
    setError(null);
    setUploadResult(null);

    const formData = new FormData();
    formData.append('file', file);

    let url = '/api/v1/ingest?';
    if (isStructured) url += `is_structured=true&`;
    if (tableName.trim()) url += `table_name=${encodeURIComponent(tableName.trim())}&`;

    try {
      const res = await fetch(url, {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Upload failed with status ${res.status}`);
      }

      const data = await res.json();
      setUploadResult(data);
      setFile(null);
      // Reset input
      const fileInput = document.getElementById('file-upload-input');
      if (fileInput) fileInput.value = '';

      // Refresh sources list
      fetchSources();
    } catch (err) {
      console.error(err);
      setError(err.message || 'Ingestion failed.');
    } finally {
      setUploading(false);
    }
  };

  const getDocTypeBadge = (docType) => {
    const typeStr = (docType || '').toLowerCase();
    if (typeStr.includes('spreadsheet') || typeStr.includes('csv') || typeStr.includes('excel')) {
      return <span className="badge badge-emerald"><Table size={12} /> Spreadsheet</span>;
    }
    if (typeStr.includes('code') || typeStr.includes('python')) {
      return <span className="badge badge-purple"><Code size={12} /> Code</span>;
    }
    if (typeStr.includes('sql') || typeStr.includes('table')) {
      return <span className="badge badge-amber"><Database size={12} /> SQL</span>;
    }
    return <span className="badge badge-cyan"><FileText size={12} /> Document</span>;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Header */}
      <div>
        <h1 style={{ 
          fontFamily: 'var(--font-display)', 
          fontSize: '2rem', 
          fontWeight: 700,
          marginBottom: '0.5rem' 
        }}>
          Multi-Modal Document &amp; Data Ingestion
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>
          Upload PDF reports, spreadsheets, markdown files, or code. The parser categorizes structure,
          extracts embedded tables, generates parent-child chunks, and indexes both vectors and SQL relational schemas.
        </p>
      </div>

      {/* Upload Zone Card */}
      <div className="glass-panel" style={{ padding: '2rem' }}>
        <div style={{
          border: '2px dashed var(--border-hover)',
          borderRadius: 'var(--radius-lg)',
          padding: '2.5rem 1.5rem',
          textAlign: 'center',
          background: 'rgba(99, 102, 241, 0.03)',
          cursor: 'pointer',
          position: 'relative',
          transition: 'all 0.2s ease'
        }}
        onClick={() => document.getElementById('file-upload-input').click()}
        >
          <input
            id="file-upload-input"
            type="file"
            onChange={handleFileChange}
            style={{ display: 'none' }}
            accept=".pdf,.csv,.xlsx,.xls,.json,.xml,.py,.md,.txt,.docx"
          />

          <div style={{
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            background: 'rgba(99, 102, 241, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1.25rem',
            color: '#a5b4fc'
          }}>
            <FileUp size={30} />
          </div>

          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', fontWeight: 600, marginBottom: '0.4rem' }}>
            {file ? file.name : 'Click to select or drop a file'}
          </div>

          <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>
            {file ? `${(file.size / 1024).toFixed(1)} KB — ready to ingest` : 'Supports PDF, CSV, Excel, Markdown, JSON, Python scripts, XML'}
          </div>
        </div>

        {/* Ingestion Configuration Options */}
        {file && (
          <div style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '1rem',
              flexWrap: 'wrap',
              background: 'rgba(255, 255, 255, 0.02)',
              padding: '1rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)'
            }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem', cursor: 'pointer' }}>
                <input
                  id="checkbox-is-structured"
                  type="checkbox"
                  checked={isStructured}
                  onChange={(e) => setIsStructured(e.target.checked)}
                  style={{ width: '16px', height: '16px', accentColor: 'var(--primary)' }}
                />
                Store as Relational SQL Table (allows SQL querying)
              </label>

              {isStructured && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: 'auto' }}>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>SQL Table Name:</span>
                  <input
                    id="input-table-name"
                    type="text"
                    placeholder="e.g. quarterly_revenue"
                    value={tableName}
                    onChange={(e) => setTableName(e.target.value)}
                    style={{
                      background: 'rgba(0, 0, 0, 0.4)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-main)',
                      padding: '0.4rem 0.75rem',
                      fontSize: '0.85rem',
                      outline: 'none',
                      fontFamily: 'var(--font-mono)'
                    }}
                  />
                </div>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                id="btn-cancel-file"
                onClick={() => setFile(null)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                id="btn-start-ingest"
                onClick={handleUpload}
                disabled={uploading}
                className="btn-primary"
              >
                {uploading ? (
                  <>
                    <RefreshCw className="animate-spin" size={16} />
                    <span>Parsing &amp; Embedding...</span>
                  </>
                ) : (
                  <>
                    <FileUp size={16} />
                    <span>Start Ingestion</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Success Banner */}
      {uploadResult && (
        <div style={{
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.35)',
          borderRadius: 'var(--radius-md)',
          padding: '1.25rem 1.5rem',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '1rem',
          color: '#6ee7b7'
        }}>
          <CheckCircle2 size={24} color="#10b981" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <div style={{ fontWeight: 700, fontSize: '1rem' }}>
              File Successfully Ingested: {uploadResult.filename}
            </div>
            <div style={{ fontSize: '0.85rem', color: '#a7f3d0' }}>
              Source ID: <code>{uploadResult.source_id}</code> &bull; 
              Total Sections: <strong>{uploadResult.total_sections || 0}</strong> &bull; 
              Total Chunks: <strong>{uploadResult.total_chunks || 0}</strong> &bull; 
              Tables Extracted: <strong>{uploadResult.total_tables || 0}</strong>
              {uploadResult.sql_table && (
                <span> &bull; SQL Table Registered: <strong>{uploadResult.sql_table}</strong></span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div style={{
          background: 'rgba(244, 63, 94, 0.1)',
          border: '1px solid rgba(244, 63, 94, 0.4)',
          borderRadius: 'var(--radius-md)',
          padding: '1rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.85rem',
          color: '#fda4af'
        }}>
          <AlertCircle size={22} color="#f43f5e" />
          <div style={{ fontSize: '0.95rem' }}>{error}</div>
        </div>
      )}

      {/* Registered Knowledge Sources Card */}
      <div className="glass-panel" style={{ padding: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <HardDrive size={20} color="#6366f1" />
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Indexed Sources &amp; Documents</h2>
          </div>
          <button
            id="btn-refresh-sources"
            onClick={fetchSources}
            disabled={loadingSources}
            className="btn-secondary"
            style={{ fontSize: '0.85rem', padding: '0.4rem 0.85rem' }}
          >
            <RefreshCw size={14} className={loadingSources ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {sources.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Source Title</th>
                  <th>Source ID</th>
                  <th>Sections</th>
                  <th>Indexed At</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((src, idx) => (
                  <tr key={idx}>
                    <td>{getDocTypeBadge(src.doc_type)}</td>
                    <td style={{ fontWeight: 600 }}>{src.title || src.source_id}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                      {src.source_id}
                    </td>
                    <td>{src.total_sections || 1}</td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                      {src.created_at ? new Date(src.created_at).toLocaleString() : 'Recent'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-dim)' }}>
            No documents ingested yet. Upload a document above to populate the knowledge base.
          </div>
        )}
      </div>
    </div>
  );
}
