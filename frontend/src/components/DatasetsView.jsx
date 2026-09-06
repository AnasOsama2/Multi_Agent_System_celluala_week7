import React, { useState, useEffect } from 'react';
import { 
  Database, 
  Table as TableIcon, 
  Columns, 
  RefreshCw, 
  HardDrive, 
  Hash, 
  Eye, 
  ChevronRight, 
  Layers,
  AlertCircle,
  FileText
} from 'lucide-react';

export default function DatasetsView() {
  const [datasets, setDatasets] = useState([]);
  const [catalogText, setCatalogText] = useState('');
  const [selectedTable, setSelectedTable] = useState(null);
  const [tableDetails, setTableDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDatasetsAndCatalog();
  }, []);

  const fetchDatasetsAndCatalog = async () => {
    setLoading(true);
    setError(null);
    try {
      const [resData, resCatalog] = await Promise.all([
        fetch('/api/v1/datasets'),
        fetch('/api/v1/schemas')
      ]);

      if (resData.ok) {
        const dJson = await resData.json();
        const list = dJson.datasets || [];
        setDatasets(list);

        if (list.length > 0 && !selectedTable) {
          const firstTableName = list[0].sql_table_name || list[0].table_name;
          handleSelectTable(firstTableName);
        }
      }

      if (resCatalog.ok) {
        const cJson = await resCatalog.json();
        setCatalogText(cJson.catalog || '');
      }
    } catch (e) {
      console.warn(e);
      setError('Failed to fetch dataset catalogs.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectTable = async (tableName) => {
    setSelectedTable(tableName);
    setLoadingDetails(true);
    try {
      const res = await fetch(`/api/v1/tables/${tableName}?limit=25`);
      if (res.ok) {
        const data = await res.json();
        setTableDetails(data);
      }
    } catch (e) {
      console.warn('Failed to load table details', e);
    } finally {
      setLoadingDetails(false);
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
            Relational SQL Datasets &amp; Schemas
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>
            Structured datasets registered in the SQLite relational store. The SQL Agent queries these tables 
            via read-only sanitized execution to answer statistical and aggregation queries.
          </p>
        </div>
        <button
          id="btn-refresh-datasets"
          onClick={fetchDatasetsAndCatalog}
          disabled={loading}
          className="btn-secondary"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh Datasets
        </button>
      </div>

      {error && (
        <div style={{
          background: 'rgba(244, 63, 94, 0.1)',
          border: '1px solid rgba(244, 63, 94, 0.4)',
          borderRadius: 'var(--radius-md)',
          padding: '1rem',
          color: '#fda4af',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* Datasets Layout: Left Sidebar for Table List, Right Area for Schema & Data */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(280px, 340px) 1fr',
        gap: '1.5rem',
        alignItems: 'start'
      }}>
        {/* Left: Datasets List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Database size={18} color="#fbbf24" />
              Registered Tables ({datasets.length})
            </h3>

            {datasets.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {datasets.map((ds, idx) => {
                  const tName = ds.sql_table_name || ds.table_name;
                  const isSelected = selectedTable === tName;
                  return (
                    <div
                      key={idx}
                      id={`dataset-item-${tName}`}
                      onClick={() => handleSelectTable(tName)}
                      style={{
                        background: isSelected ? 'rgba(99, 102, 241, 0.18)' : 'rgba(255, 255, 255, 0.02)',
                        border: isSelected ? '1px solid var(--border-accent)' : '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-md)',
                        padding: '0.85rem 1rem',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between'
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '0.95rem', color: isSelected ? '#a5b4fc' : 'var(--text-main)', wordBreak: 'break-all' }}>
                          {tName}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
                          {ds.source_file || 'CSV Source'} &bull; {ds.sheet_name || 'Sheet'}
                        </div>
                      </div>
                      <ChevronRight size={18} color={isSelected ? '#6366f1' : 'var(--text-dim)'} />
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ color: 'var(--text-dim)', fontSize: '0.9rem', textAlign: 'center', padding: '1.5rem 0' }}>
                No relational datasets loaded yet.
              </div>
            )}
          </div>

          {/* Full Schema Catalog Card */}
          {catalogText && (
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <h4 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)' }}>
                <FileText size={16} color="#06b6d4" />
                Introspection Catalog
              </h4>
              <pre style={{
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.75rem',
                fontSize: '0.75rem',
                fontFamily: 'var(--font-mono)',
                color: '#94a3b8',
                maxHeight: '260px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap'
              }}>
                {catalogText}
              </pre>
            </div>
          )}
        </div>

        {/* Right: Schema & Data Viewer */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {selectedTable ? (
            <>
              {/* Schema Inspector Card */}
              <div className="glass-panel" style={{ padding: '1.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <Columns size={20} color="#06b6d4" />
                    <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>
                      Schema: <code>{selectedTable}</code>
                    </h3>
                  </div>
                  <span className="badge badge-cyan">
                    {tableDetails?.columns?.length || 0} Columns
                  </span>
                </div>

                <div style={{ overflowX: 'auto' }}>
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>Column Name</th>
                        <th>Data Type</th>
                        <th>Nullable</th>
                        <th>Description / Sample</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(tableDetails?.columns || []).map((col, cIdx) => (
                        <tr key={cIdx}>
                          <td style={{ fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{col.column_name}</td>
                          <td>
                            <span className="badge badge-purple" style={{ fontFamily: 'var(--font-mono)' }}>
                              {col.data_type || 'TEXT'}
                            </span>
                          </td>
                          <td>{col.is_nullable ? 'Yes' : 'No'}</td>
                          <td style={{ color: 'var(--text-dim)', fontSize: '0.85rem' }}>
                            {col.description || (col.sample_values ? (Array.isArray(col.sample_values) ? col.sample_values.slice(0, 3).join(', ') : String(col.sample_values)) : '-')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Data Preview Card */}
              <div className="glass-panel" style={{ padding: '1.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <Eye size={20} color="#10b981" />
                    <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>
                      Data Preview ({tableDetails?.sample_rows?.length || 0} Sample Records)
                    </h3>
                  </div>
                </div>

                {loadingDetails ? (
                  <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    Loading table rows...
                  </div>
                ) : tableDetails && tableDetails.sample_rows && tableDetails.sample_rows.length > 0 ? (
                  <div style={{ overflowX: 'auto', maxHeight: '420px' }}>
                    <table className="custom-table">
                      <thead>
                        <tr>
                          {Object.keys(tableDetails.sample_rows[0]).map((key, idx) => (
                            <th key={idx} style={{ position: 'sticky', top: 0, zIndex: 2 }}>{key}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {tableDetails.sample_rows.map((row, rIdx) => (
                          <tr key={rIdx}>
                            {Object.values(row).map((val, vIdx) => (
                              <td key={vIdx}>{val !== null && val !== undefined ? String(val) : '-'}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-dim)' }}>
                    No sample records returned for table.
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-dim)' }}>
              Select a table from the left to view its schema and browse sample records.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
