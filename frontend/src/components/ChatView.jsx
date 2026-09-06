import React, { useState, useRef } from 'react';
import { 
  Send, 
  Sparkles, 
  Bot, 
  FileText, 
  Database, 
  Cpu, 
  CheckCircle2, 
  AlertTriangle, 
  ChevronDown, 
  ChevronUp, 
  Table as TableIcon, 
  BookOpen, 
  Calculator, 
  Clock, 
  Code,
  Layers,
  RotateCcw
} from 'lucide-react';

export default function ChatView() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('answer'); // 'answer' | 'findings' | 'tables' | 'sql' | 'sources'
  const [expandedFinding, setExpandedFinding] = useState(null);
  const responseRef = useRef(null);

  const sampleQueries = [
    { label: '📊 SQL Ticket Analysis', text: 'How many tickets have High priority and who are the customers?' },
    { label: '🤖 Multi-Agent Architecture', text: 'Summarize the multi-agent architecture and retrieval confidence pipeline.' },
    { label: '📑 Hybrid Document Search', text: 'What is the rate limit and burst capability for standard and premium users?' },
    { label: '🧮 Budget & Cost Drivers', text: 'Calculate the total budget variance and highlight the top 3 cost drivers.' },
  ];

  const handleSend = async (queryText = query) => {
    const textToSend = queryText.trim();
    if (!textToSend || loading) return;

    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: textToSend, max_results: 15 })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${res.status}`);
      }

      const data = await res.json();
      setResult(data);
      setActiveTab('answer');
      if (responseRef.current) {
        setTimeout(() => {
          responseRef.current.scrollIntoView({ behavior: 'smooth' });
        }, 100);
      }
    } catch (err) {
      console.error(err);
      setError(err.message || 'An unexpected error occurred while executing the query.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Helper to render citation badges nicely in text
  const renderFormattedText = (text) => {
    if (!text) return null;
    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, idx) => {
      const match = part.match(/^\[(\d+)\]$/);
      if (match) {
        return (
          <span 
            key={idx} 
            className="citation-tag" 
            title={`Source citation [${match[1]}]`}
            onClick={() => setActiveTab('sources')}
          >
            [{match[1]}]
          </span>
        );
      }
      return part;
    });
  };

  // Normalize response fields across API versions
  const currentAnswer = result ? (result.final_answer || result.answer || '') : '';
  const currentRoute = result ? (result.routed_to || result.route || 'hybrid') : '';
  const currentConfidence = result ? (
    result.retrieval_confidence !== undefined ? result.retrieval_confidence : 
    (result.confidence_score !== undefined ? result.confidence_score : 0.85)
  ) : 0.85;
  const isHighConfidence = result ? (result.is_high_confidence || currentConfidence >= 0.75) : false;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Hero / Header Section */}
      <div style={{ textAlign: 'center', maxWidth: '800px', margin: '0 auto' }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          background: 'rgba(99, 102, 241, 0.12)',
          border: '1px solid rgba(99, 102, 241, 0.3)',
          borderRadius: '9999px',
          padding: '0.35rem 1rem',
          fontSize: '0.85rem',
          color: '#a5b4fc',
          marginBottom: '1rem'
        }}>
          <Sparkles size={16} />
          Collaborative Multi-Agent Triad: Retrieval &bull; Analyst &bull; Answer
        </div>
        <h1 style={{ 
          fontFamily: 'var(--font-display)', 
          fontSize: '2.5rem', 
          fontWeight: 800, 
          letterSpacing: '-0.03em',
          background: 'linear-gradient(135deg, #ffffff 40%, #94a3b8 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          marginBottom: '0.85rem'
        }}>
          Query, Analyze &amp; Synthesize with Grounded Rigor
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '1.05rem', lineHeight: 1.6 }}>
          Ask questions across unstructured PDFs, spreadsheets, and SQL databases. 
          The Retriever routes and finds evidence, the Analyst verifies sufficiency and calculates tables, 
          and the Answer Agent delivers grounded cited answers.
        </p>
      </div>

      {/* Query Input Card */}
      <div className="glass-panel" style={{ padding: '1.75rem', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '2px',
          background: 'linear-gradient(90deg, #6366f1, #06b6d4, #10b981)'
        }} />

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ position: 'relative' }}>
            <textarea
              id="query-input"
              rows={3}
              placeholder="Ask a question across your documents, tables, or databases (e.g., 'How many tickets have High priority and who are the customers?')..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              style={{
                width: '100%',
                background: 'rgba(10, 13, 20, 0.65)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-main)',
                fontFamily: 'var(--font-sans)',
                fontSize: '1rem',
                padding: '1rem 1.25rem',
                outline: 'none',
                resize: 'vertical',
                transition: 'border-color 0.2s ease, box-shadow 0.2s ease'
              }}
              onFocus={(e) => {
                e.target.style.borderColor = 'var(--border-accent)';
                e.target.style.boxShadow = '0 0 15px var(--primary-glow)';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = 'var(--border-subtle)';
                e.target.style.boxShadow = 'none';
              }}
            />
          </div>

          {/* Action Row: Samples + Submit */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            flexWrap: 'wrap', 
            gap: '1rem' 
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontWeight: 600 }}>Try sample:</span>
              {sampleQueries.map((sample, idx) => (
                <button
                  key={idx}
                  id={`sample-query-${idx}`}
                  onClick={() => {
                    setQuery(sample.text);
                    handleSend(sample.text);
                  }}
                  className="btn-secondary"
                  style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem', borderRadius: '20px' }}
                >
                  {sample.label}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {query && (
                <button
                  id="btn-clear-query"
                  onClick={() => { setQuery(''); setResult(null); }}
                  className="btn-secondary"
                  style={{ padding: '0.75rem 1rem' }}
                  title="Clear Query"
                >
                  <RotateCcw size={16} />
                </button>
              )}
              <button
                id="btn-submit-query"
                onClick={() => handleSend()}
                disabled={loading || !query.trim()}
                className="btn-primary"
                style={{ minWidth: '140px' }}
              >
                {loading ? (
                  <>
                    <Cpu className="animate-spin" size={18} />
                    <span>Reasoning...</span>
                  </>
                ) : (
                  <>
                    <Send size={18} />
                    <span>Run Query</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

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
          <AlertTriangle size={22} color="#f43f5e" />
          <div style={{ flex: 1, fontSize: '0.95rem' }}>{error}</div>
        </div>
      )}

      {/* Results Container */}
      {result && (
        <div ref={responseRef} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Multi-Agent Reasoning Pipeline Bar */}
          <div className="glass-panel" style={{ padding: '1.25rem 1.5rem' }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between', 
              marginBottom: '1rem',
              flexWrap: 'wrap',
              gap: '0.5rem'
            }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Multi-Agent Workflow Trajectory
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                {result.trace_id && (
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    Trace: {result.trace_id}
                  </span>
                )}
                <span className="badge badge-purple" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Clock size={12} /> {result.execution_time_ms ? `${result.execution_time_ms.toFixed(0)} ms` : 'Complete'}
                </span>
                <span className="badge badge-cyan">
                  Route: {currentRoute.toUpperCase()}
                </span>
              </div>
            </div>

            {/* Stepper Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: '1rem'
            }}>
              {/* Step 1: Retrieval Agent */}
              <div style={{
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '1rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
                  <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: 'rgba(6, 182, 212, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Layers size={16} color="#06b6d4" />
                  </div>
                  <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>1. Retriever Agent</span>
                  <CheckCircle2 size={16} color="#10b981" style={{ marginLeft: 'auto' }} />
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  Confidence: <strong style={{ color: isHighConfidence ? '#34d399' : '#fbbf24' }}>
                    {(currentConfidence * 100).toFixed(0)}%
                  </strong>
                  <br />
                  Reranked: <span style={{ color: result.reranked ? '#38bdf8' : 'var(--text-dim)' }}>
                    {result.reranked ? 'Yes (BGE-Reranker)' : 'Direct Match'}
                  </span>
                  <br />
                  Sources: {result.sources?.length || 0} references found
                </div>
              </div>

              {/* Step 2: Analyst Agent */}
              <div style={{
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '1rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
                  <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: 'rgba(168, 85, 247, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Cpu size={16} color="#a855f7" />
                  </div>
                  <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>2. Analyst Agent</span>
                  <CheckCircle2 size={16} color="#10b981" style={{ marginLeft: 'auto' }} />
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  Sufficiency: <strong style={{ color: '#34d399' }}>
                    {typeof result.sufficiency === 'string' ? result.sufficiency : (result.sufficiency?.is_sufficient ? 'Sufficient' : 'Evaluated')}
                  </strong>
                  <br />
                  Findings: {result.findings?.length || 0} claims verified
                  <br />
                  Iterations: {result.iterations_used !== undefined ? result.iterations_used : 0} loop(s)
                </div>
              </div>

              {/* Step 3: Answer Agent */}
              <div style={{
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '1rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
                  <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: 'rgba(99, 102, 241, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Bot size={16} color="#6366f1" />
                  </div>
                  <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>3. Answer Agent</span>
                  <CheckCircle2 size={16} color="#10b981" style={{ marginLeft: 'auto' }} />
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  Synthesis: Grounded &amp; Cited
                  <br />
                  Citations: {result.citations?.length || 0} formatted
                  <br />
                  Quality Gate: {result.feedback_passed ? 'Passed' : 'Evaluated'}
                </div>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border-subtle)', gap: '0.5rem', overflowX: 'auto' }}>
            <button
              id="tab-answer"
              onClick={() => setActiveTab('answer')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem 1.25rem',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === 'answer' ? '2px solid var(--primary)' : '2px solid transparent',
                color: activeTab === 'answer' ? '#ffffff' : 'var(--text-muted)',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              <Bot size={18} />
              Final Answer
            </button>

            <button
              id="tab-findings"
              onClick={() => setActiveTab('findings')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem 1.25rem',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === 'findings' ? '2px solid var(--accent-purple)' : '2px solid transparent',
                color: activeTab === 'findings' ? '#ffffff' : 'var(--text-muted)',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              <FileText size={18} />
              Analyst Findings ({result.findings?.length || 0})
            </button>

            {result.tables && result.tables.length > 0 && (
              <button
                id="tab-tables"
                onClick={() => setActiveTab('tables')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem 1.25rem',
                  background: 'none',
                  border: 'none',
                  borderBottom: activeTab === 'tables' ? '2px solid var(--accent-cyan)' : '2px solid transparent',
                  color: activeTab === 'tables' ? '#ffffff' : 'var(--text-muted)',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <TableIcon size={18} />
                Extracted Tables ({result.tables.length})
              </button>
            )}

            {result.sql_executed && (
              <button
                id="tab-sql"
                onClick={() => setActiveTab('sql')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem 1.25rem',
                  background: 'none',
                  border: 'none',
                  borderBottom: activeTab === 'sql' ? '2px solid var(--accent-amber)' : '2px solid transparent',
                  color: activeTab === 'sql' ? '#ffffff' : 'var(--text-muted)',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <Database size={18} />
                SQL Execution
              </button>
            )}

            <button
              id="tab-sources"
              onClick={() => setActiveTab('sources')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem 1.25rem',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === 'sources' ? '2px solid var(--accent-emerald)' : '2px solid transparent',
                color: activeTab === 'sources' ? '#ffffff' : 'var(--text-muted)',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              <BookOpen size={18} />
              Grounded Sources ({result.sources?.length || 0})
            </button>
          </div>

          {/* TAB 1: FINAL ANSWER */}
          {activeTab === 'answer' && (
            <div className="glass-panel" style={{ padding: '2rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
                <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.35rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <Sparkles size={20} color="#6366f1" />
                  Synthesized Grounded Answer
                </h2>
                <span className="badge badge-emerald">Verified Grounding</span>
              </div>

              <div style={{ 
                fontSize: '1.05rem', 
                lineHeight: 1.8, 
                color: 'var(--text-main)', 
                whiteSpace: 'pre-wrap',
                fontFamily: 'var(--font-sans)'
              }}>
                {renderFormattedText(currentAnswer)}
              </div>

              {/* Citations Footer */}
              {result.citations && result.citations.length > 0 && (
                <div style={{ marginTop: '2rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    References &amp; Grounding Evidence
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {result.citations.map((cit, idx) => {
                      const marker = cit.marker || `[${cit.number || idx + 1}]`;
                      const doc = cit.document || cit.title || cit.source_id;
                      const snippet = cit.snippet || (cit.page ? `page ${cit.page}` : '');
                      return (
                        <div key={idx} style={{ fontSize: '0.85rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
                          <span className="citation-tag">{marker}</span>
                          <span style={{ color: 'var(--text-muted)' }}>{doc}</span>
                          {snippet && (
                            <span style={{ fontStyle: 'italic', color: 'var(--text-dim)' }}>
                              &mdash; {snippet}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: FINDINGS */}
          {activeTab === 'findings' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {result.findings && result.findings.length > 0 ? (
                result.findings.map((finding, idx) => {
                  const isExpanded = expandedFinding === idx;
                  const claimText = finding.claim || finding.statement || `Claim ${idx + 1}`;
                  const reasoning = finding.reasoning || finding.explanation || '';
                  const evidence = finding.evidence || (Array.isArray(finding.supporting_evidence) ? finding.supporting_evidence.join(', ') : finding.supporting_evidence) || '';
                  const conf = finding.confidence !== undefined ? finding.confidence : 0.9;
                  const calc = finding.calculation || finding.calc;

                  return (
                    <div key={idx} className="glass-panel" style={{ padding: '1.25rem 1.5rem' }}>
                      <div 
                        style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', cursor: 'pointer', gap: '1rem' }}
                        onClick={() => setExpandedFinding(isExpanded ? null : idx)}
                      >
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem' }}>
                          <span className="badge badge-purple">Claim {idx + 1}</span>
                          <span style={{ fontWeight: 600, fontSize: '1.05rem', color: 'var(--text-main)' }}>
                            {claimText}
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
                          <span className="badge badge-emerald">
                            {(conf * 100).toFixed(0)}% Conf
                          </span>
                          {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </div>
                      </div>

                      {isExpanded && (
                        <div style={{ marginTop: '1.25rem', paddingTop: '1.25rem', borderTop: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                          {reasoning && (
                            <div>
                              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>Reasoning:</span>
                              <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>{reasoning}</div>
                            </div>
                          )}

                          {evidence && (
                            <div>
                              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase' }}>Supporting Evidence:</span>
                              <div style={{ 
                                fontSize: '0.85rem', 
                                color: 'var(--text-muted)', 
                                background: 'rgba(0, 0, 0, 0.3)', 
                                padding: '0.75rem 1rem', 
                                borderRadius: 'var(--radius-sm)',
                                marginTop: '0.25rem',
                                borderLeft: '3px solid var(--primary)'
                              }}>
                                {evidence}
                              </div>
                            </div>
                          )}

                          {calc && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(245, 158, 11, 0.1)', padding: '0.5rem 0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                              <Calculator size={16} color="#fbbf24" />
                              <span style={{ fontSize: '0.85rem', color: '#fbbf24', fontFamily: 'var(--font-mono)' }}>
                                Calculation: {calc}
                              </span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No standalone analytical claims generated.
                </div>
              )}
            </div>
          )}

          {/* TAB 3: EXTRACTED TABLES */}
          {activeTab === 'tables' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {result.tables && result.tables.map((table, idx) => (
                <div key={idx} className="glass-panel" style={{ padding: '1.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                      <TableIcon size={20} color="#06b6d4" />
                      <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>{table.title || `Extracted Table ${idx + 1}`}</h3>
                    </div>
                    {table.source_id && (
                      <span className="badge badge-cyan">{table.source_id}</span>
                    )}
                  </div>

                  <div style={{ overflowX: 'auto' }}>
                    <table className="custom-table">
                      <thead>
                        <tr>
                          {table.headers?.map((h, hIdx) => (
                            <th key={hIdx}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {table.rows?.map((row, rIdx) => (
                          <tr key={rIdx}>
                            {row.map((cell, cIdx) => (
                              <td key={cIdx}>{cell !== null && cell !== undefined ? String(cell) : '-'}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {table.notes && (
                    <div style={{ marginTop: '1rem', fontSize: '0.8rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                      * {table.notes}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* TAB 4: SQL EXECUTION */}
          {activeTab === 'sql' && (
            <div className="glass-panel" style={{ padding: '1.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1rem' }}>
                <Database size={20} color="#fbbf24" />
                <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Generated &amp; Executed SQL</h3>
              </div>

              <pre style={{
                background: 'rgba(0, 0, 0, 0.5)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '1rem 1.25rem',
                color: '#38bdf8',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.9rem',
                overflowX: 'auto',
                marginBottom: '1.5rem'
              }}>
                <code>{result.sql_executed}</code>
              </pre>

              {result.sql_rows_count !== undefined && (
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                  Rows processed: <strong>{result.sql_rows_count}</strong>
                </div>
              )}

              {result.sql_results && result.sql_results.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                    Returned Records ({result.sql_results.length})
                  </div>
                  <div style={{ overflowX: 'auto' }}>
                    <table className="custom-table">
                      <thead>
                        <tr>
                          {Object.keys(result.sql_results[0]).map((colKey, idx) => (
                            <th key={idx}>{colKey}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {result.sql_results.map((row, rIdx) => (
                          <tr key={rIdx}>
                            {Object.values(row).map((val, cIdx) => (
                              <td key={cIdx}>{val !== null && val !== undefined ? String(val) : '-'}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 5: GROUNDED SOURCES */}
          {activeTab === 'sources' && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }}>
              {result.sources && result.sources.length > 0 ? (
                result.sources.map((src, idx) => {
                  if (typeof src === 'string') {
                    return (
                      <div key={idx} className="glass-panel" style={{ padding: '1.25rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                          <span className="badge badge-emerald">Source [{idx + 1}]</span>
                        </div>
                        <div style={{ fontSize: '0.9rem', color: 'var(--text-main)', lineHeight: 1.5 }}>
                          {src}
                        </div>
                      </div>
                    );
                  }
                  return (
                    <div key={idx} className="glass-panel" style={{ padding: '1.25rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                        <span className="badge badge-emerald">Source [{idx + 1}]</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
                          {src.doc_type || 'Document'}
                        </span>
                      </div>
                      <h4 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-main)' }}>
                        {src.title || src.source_id}
                      </h4>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', wordBreak: 'break-all' }}>
                        URI: {src.uri || 'local:ingested'}
                      </div>
                      {src.total_sections && (
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                          Sections: {src.total_sections}
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', gridColumn: '1 / -1' }}>
                  No explicit sources registered for this query.
                </div>
              )}
            </div>
          )}

        </div>
      )}
    </div>
  );
}
