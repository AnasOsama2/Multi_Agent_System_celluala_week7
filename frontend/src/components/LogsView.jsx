import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Cpu, 
  Database, 
  Layers, 
  ShieldCheck, 
  Clock, 
  CheckCircle2, 
  Terminal, 
  RefreshCw,
  GitBranch,
  Network
} from 'lucide-react';

export default function LogsView() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchHealth();
  }, []);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/health');
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch (e) {
      console.warn('Failed to fetch system telemetry', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ 
            fontFamily: 'var(--font-display)', 
            fontSize: '2rem', 
            fontWeight: 700,
            marginBottom: '0.5rem' 
          }}>
            Multi-Agent System Observability &amp; Architecture
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>
            Real-time pipeline diagnostics, telemetry stats, and LangGraph multi-agent execution flow.
          </p>
        </div>
        <button
          id="btn-refresh-health"
          onClick={fetchHealth}
          disabled={loading}
          className="btn-secondary"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh Telemetry
        </button>
      </div>

      {/* Telemetry Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        gap: '1.25rem'
      }}>
        {/* Backend Status */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)', fontWeight: 600, textTransform: 'uppercase' }}>System Status</span>
            <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#10b981', boxShadow: '0 0 10px #10b981' }} />
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#10b981', fontFamily: 'var(--font-display)' }}>
            {health?.status === 'ok' ? 'HEALTHY & OPERATIONAL' : 'ONLINE'}
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
            FastAPI + LangGraph Execution Engine
          </div>
        </div>

        {/* Vector Store */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)', fontWeight: 600, textTransform: 'uppercase' }}>Vector Index (Chroma)</span>
            <Layers size={18} color="#06b6d4" />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, fontFamily: 'var(--font-display)' }}>
            {health?.vector_count !== undefined ? health.vector_count : '-'}
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
            Indexed Chunks &bull; 1024-d BAAI/bge-m3
          </div>
        </div>

        {/* Relational Store */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)', fontWeight: 600, textTransform: 'uppercase' }}>Relational Tables (SQLite)</span>
            <Database size={18} color="#fbbf24" />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, fontFamily: 'var(--font-display)' }}>
            {health?.sql_tables !== undefined ? health.sql_tables : '-'}
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
            Registered Dynamic Tables &bull; Read-Only
          </div>
        </div>

        {/* Model Spec */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)', fontWeight: 600, textTransform: 'uppercase' }}>LLM Backbone</span>
            <Cpu size={18} color="#a855f7" />
          </div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'var(--font-display)', color: '#c084fc' }}>
            qwen/qwen3.8-27b
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
            Groq High-Speed Inference (Max 800 tokens)
          </div>
        </div>
      </div>

      {/* Multi-Agent Architecture Diagram Box */}
      <div className="glass-panel" style={{ padding: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.5rem' }}>
          <Network size={22} color="#6366f1" />
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700 }}>End-to-End Multi-Agent Architecture Flow</h2>
        </div>

        <div style={{
          background: 'rgba(10, 13, 20, 0.75)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '1.5rem',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.85rem',
          lineHeight: 1.7,
          color: '#e2e8f0',
          overflowX: 'auto'
        }}>
          <div style={{ color: '#818cf8', fontWeight: 700 }}>[1] INGESTION &amp; INDEXING STAGE:</div>
          <div style={{ paddingLeft: '1.5rem', color: 'var(--text-muted)' }}>
            Files (PDF, XLSX, CSV, JSON, Code, MD) &rarr; Detector &rarr; Parsers (Document / PDF-Table / Spreadsheet / Code)<br />
            &rarr; Parent-Child Chunking (Parent sections + 250-500 token children with heading breadcrumbs)<br />
            &rarr; SQLite Storage (Sources, Datasets, Column Schemas, Tables) + ChromaDB (Dense) + BM25Okapi (Keyword)
          </div>

          <div style={{ color: '#38bdf8', fontWeight: 700, marginTop: '1.25rem' }}>[2] RETRIEVAL &amp; ROUTING STAGE:</div>
          <div style={{ paddingLeft: '1.5rem', color: 'var(--text-muted)' }}>
            User Query &rarr; Query Preprocessing &rarr; Route Query (SQL | Hybrid | Mixed)<br />
            &bull; <span style={{ color: '#fbbf24' }}>SQL Path:</span> Schema introspection &rarr; Groq SQL Generation &rarr; Read-Only Execution &rarr; Formatted Table<br />
            &bull; <span style={{ color: '#34d399' }}>Hybrid Path:</span> Chroma Dense (1024-d) + BM25 Sparse &rarr; Reciprocal Rank Fusion &rarr; Confidence Gate (0.75)<br />
            &bull; <span style={{ color: '#f43f5e' }}>Confidence Check:</span> Score &ge; 0.75 (High) &rarr; Direct Context; Score &lt; 0.75 (Low) &rarr; BGE-Reranker-v2-m3
          </div>

          <div style={{ color: '#c084fc', fontWeight: 700, marginTop: '1.25rem' }}>[3] ANALYST AGENT STAGE (Answer&amp;Analyst Integration):</div>
          <div style={{ paddingLeft: '1.5rem', color: 'var(--text-muted)' }}>
            Analyst Agent receives Evidence &rarr; Sufficiency Assessment (`is_sufficient`)<br />
            &bull; If insufficient &amp; iterations &lt; 2 &rarr; Feedback loop to Retriever with refined queries<br />
            &bull; Executes Analyst Tools: CalculatorTool, TableExtractorTool, DocumentComparisonTool, DataAnalysisTool<br />
            &rarr; Constructs verified `AnalysisFinding`s with claims, evidence, and confidence
          </div>

          <div style={{ color: '#34d399', fontWeight: 700, marginTop: '1.25rem' }}>[4] ANSWER AGENT STAGE:</div>
          <div style={{ paddingLeft: '1.5rem', color: 'var(--text-muted)' }}>
            Answer Agent executes CitationFormatterTool &amp; SourceFormatterTool<br />
            &rarr; Generates grounded synthesis with inline citation tags [1], [2] strictly anchored to evidence<br />
            &rarr; Evaluates feedback loop (if exact match / low quality, triggers fallback search) &rarr; Returns Grounded Output
          </div>
        </div>
      </div>

      {/* State Schema Card */}
      <div className="glass-panel" style={{ padding: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.25rem' }}>
          <GitBranch size={20} color="#06b6d4" />
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>LangGraph Unified State Definition (`RAGState`)</h3>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="custom-table">
            <thead>
              <tr>
                <th>State Property</th>
                <th>Type</th>
                <th>Originating Agent</th>
                <th>Role in Multi-Agent Trajectory</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>query</td>
                <td>str</td>
                <td>User / Input</td>
                <td>Original user query input string</td>
              </tr>
              <tr>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>routed_to</td>
                <td>'sql' | 'hybrid' | 'mixed'</td>
                <td>Retriever Router</td>
                <td>Directs flow to SQL generator, Hybrid search, or both</td>
              </tr>
              <tr>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>retrieval_confidence</td>
                <td>float [0.0 - 1.0]</td>
                <td>Confidence Gate</td>
                <td>Evaluates whether retrieval is sufficient or requires reranking</td>
              </tr>
              <tr>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>reranked</td>
                <td>bool</td>
                <td>BGE-Reranker</td>
                <td>Indicates whether cross-encoder re-ordered candidates</td>
              </tr>
              <tr>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>evidence_chunks</td>
                <td>list[EvidenceChunk]</td>
                <td>PipelineRetrieverAdapter</td>
                <td>Adapter-converted evidence passed into Analyst Agent</td>
              </tr>
              <tr>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>findings</td>
                <td>list[AnalysisFinding]</td>
                <td>Analyst Agent</td>
                <td>Verified analytical claims with grounded evidence and math</td>
              </tr>
              <tr>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>sufficiency</td>
                <td>SufficiencyAssessment</td>
                <td>Analyst Agent</td>
                <td>Determines if retrieved evidence is complete or needs more search</td>
              </tr>
              <tr>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>tables</td>
                <td>list[ExtractedTable]</td>
                <td>Analyst Tool</td>
                <td>Structured extracted tables with headers, rows, and notes</td>
              </tr>
              <tr>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>citations</td>
                <td>list[dict]</td>
                <td>Answer Agent</td>
                <td>Numbered inline citations mapped to source titles and snippets</td>
              </tr>
              <tr>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>final_answer</td>
                <td>str</td>
                <td>Answer Agent</td>
                <td>Synthesized grounded answer returned to client</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
