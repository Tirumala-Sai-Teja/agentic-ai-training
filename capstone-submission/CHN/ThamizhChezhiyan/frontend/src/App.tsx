import { useEffect, useState } from 'react'
import './index.css'
import { checkHealth, getStatus, processFolder, processUpload, getReviewQueue, submitReviewDecision, getAuditLogs, resetSystem, shutdownSystem } from './api/client'

type DocumentResult = {
  document_name: string
  classification: string
  confidence: number
  processing_status: string
  document_content?: string
}

type AuditEntry = {
  timestamp: string
  agent_name: string
  action: string
  document_name?: string
  classification?: string
  status: string
  explanation?: string
}

type TabType = 'dashboard' | 'documents' | 'review' | 'audit' | 'settings'
type ThemeType = 'light' | 'dark' | 'system'

const App = () => {
  const [activeTab, setActiveTab] = useState<TabType>('dashboard')
  const [theme, setTheme] = useState<ThemeType>('dark')
  const [health, setHealth] = useState('unknown')
  const [status, setStatus] = useState<any>(null)
  const [folderPath, setFolderPath] = useState('')
  const [processing, setProcessing] = useState(false)
  const [results, setResults] = useState<DocumentResult[]>([])
  const [reviewQueue, setReviewQueue] = useState<any[]>([])
  const [selectedReviewDoc, setSelectedReviewDoc] = useState<any>(null)
  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([])
  const [message, setMessage] = useState('')
  const [showResetConfirm, setShowResetConfirm] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null)
  const [lastLoadedCount, setLastLoadedCount] = useState(0)

  useEffect(() => {
    loadInitialData()
    applyTheme()
  }, [theme])

  useEffect(() => {
    if (!message) return

    const timer = setTimeout(() => setMessage(''), 3000)

    const clearMessage = () => setMessage('')
    window.addEventListener('click', clearMessage)

    return () => {
      clearTimeout(timer)
      window.removeEventListener('click', clearMessage)
    }
  }, [message])

  const loadInitialData = async () => {
    try {
      // Memory cleanup: free large state before loading new data
      setStatus(null)
      setReviewQueue([])
      setAuditLogs([])
      setSelectedFiles(null)
      setSelectedReviewDoc(null)
      setFolderPath('')

      const [healthRes, statusRes, queueRes, auditRes] = await Promise.all([
        checkHealth(),
        getStatus(),
        getReviewQueue(),
        getAuditLogs()
      ])

      setHealth(healthRes.status)
      setStatus(statusRes.system)
      setReviewQueue(queueRes.queue)
      setAuditLogs(auditRes.logs)
    } catch (error) {
      console.error('Failed to load initial data:', error)
    }
  }

  const applyTheme = () => {
    const root = document.documentElement
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    const activeTheme = theme === 'system' ? systemTheme : theme

    root.setAttribute('data-theme', activeTheme)
  }

  const handleThemeChange = (newTheme: ThemeType) => {
    setTheme(newTheme)
    localStorage.setItem('edps-theme', newTheme)
  }

  useEffect(() => {
    const savedTheme = localStorage.getItem('edps-theme') as ThemeType
    if (savedTheme) {
      setTheme(savedTheme)
    }
  }, [])

  const handleProcessFolder = async () => {
    if (!folderPath) {
      setMessage('Please provide a folder path')
      return
    }

    setProcessing(true)
    setMessage('Processing folder...')

    try {
      const response = await processFolder(folderPath)
      setResults(response.results)
      setMessage(`Processed ${response.documents} documents`)
      await loadInitialData() // Refresh status
    } catch (error: any) {
      setMessage(error.message ?? 'Failed to process folder')
    } finally {
      setProcessing(false)
    }
  }

  const handleFileSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    setSelectedFiles(files)
  }

  const handleLoadDocuments = async () => {
    if (!selectedFiles || selectedFiles.length === 0) {
      setMessage('Please select files to load')
      return
    }

    setProcessing(true)
    setMessage(`Processing ${selectedFiles.length} file(s)...`)
    setResults([]) // Clear previous results to keep UI responsive

    try {
      const promises = Array.from(selectedFiles).map(file => {
        const formData = new FormData()
        formData.append('file', file)
        return processUpload(formData)
      })
      const responses = await Promise.all(promises)
      setResults(responses.map(r => r.result))
      setLastLoadedCount(selectedFiles.length)
      setMessage(`Successfully loaded and processed ${selectedFiles.length} document(s)`)
      setSelectedFiles(null)
      // Reset file input
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
      if (fileInput) fileInput.value = ''
      await loadInitialData()
    } catch (error: any) {
      setMessage(error.message ?? 'Upload failed')
    } finally {
      setProcessing(false)
    }
  }

  const handleSubmitReview = async (documentName: string, decision: string, notes?: string) => {
    const reviewer_notes = notes || `Reviewed via modern UI at ${new Date().toISOString()}`
    try {
      await submitReviewDecision({ document_name: documentName, human_decision: decision, reviewer_notes })
      setMessage(`Review decision submitted: ${decision}`)
      await loadInitialData() // Refresh queue and status
    } catch (error: any) {
      setMessage(error.message ?? 'Failed to submit review')
    }
  }

  const handleResetSystem = async () => {
    if (!showResetConfirm) {
      setShowResetConfirm(true)
      try {
        await resetSystem()
        // Memory cleanup: free all large state on frontend
        setStatus(null)
        setResults([])
        setReviewQueue([])
        setAuditLogs([])
        setSelectedReviewDoc(null)
        setLastLoadedCount(0)
        setSelectedFiles(null)
        setFolderPath('')
        setMessage('System reset complete')
        setShowResetConfirm(false)
        // Also clear any file input
        const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
        if (fileInput) fileInput.value = ''
        await loadInitialData() // Reload fresh data
      } catch (error: any) {
        setMessage(error.message ?? 'Reset failed')
      }
    }
  }

  const handleSignOut = async () => {
    setMessage('Signing out and shutting down services...')
    try {
      if (typeof window.stop === 'function') {
        window.stop()
      }
      await shutdownSystem()
      setMessage('Services stopped. Closing UI...')
      setTimeout(() => {
        window.open('', '_self')
        window.location.href = 'about:blank'
        window.close()
      }, 400)
    } catch (error: any) {
      setMessage(error.message ?? 'Sign out failed')
    }
  }

  const renderDashboard = () => (
    <div className="dashboard">
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Documents</h3>
          <div className="stat-value">{status?.database_stats?.total_documents ?? 0}</div>
        </div>
        <div className="stat-card">
          <h3>Cease & Desist</h3>
          <div className="stat-value" style={{ color: '#10b981' }}>
            {status?.database_stats?.cease_requests ?? 0}
          </div>
        </div>
        <div className="stat-card">
          <h3>Irrelevant</h3>
          <div className="stat-value" style={{ color: '#ef4444' }}>
            {status?.archive_stats?.total_archived ?? 0}
          </div>
        </div>
        <div className="stat-card">
          <h3>Pending Reviews</h3>
          <div className="stat-value">{reviewQueue.length}</div>
        </div>
        <div className="stat-card">
          <h3>System Health</h3>
          <div className="health-indicator">
            <div className={`status-light ${health === 'ok' ? 'healthy' : 'unhealthy'}`}></div>
            <span className={`status-text ${health === 'ok' ? 'healthy' : 'unhealthy'}`}>
              {health === 'ok' ? 'Operational' : 'Offline'}
            </span>
          </div>
        </div>
        <div className="stat-card">
          <h3>Recent Activity</h3>
          <div className="stat-value">{lastLoadedCount}</div>
        </div>
      </div>

      <div className="recent-activity">
        <h3>Recent Activity</h3>
        <div className="activity-list">
          {auditLogs.slice(0, 5).map((log: AuditEntry, index: number) => (
            <div key={index} className="activity-item">
              <div className="activity-time">{new Date(log.timestamp).toLocaleString()}</div>
              <div className="activity-content">
                <strong>{log.agent_name}</strong>: {log.action}
                {log.document_name && <span> - {log.document_name}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )

  const renderDocuments = () => (
    <div className="documents">
      <div className="processing-section">
        <div className="card">
          <h3>📄 Load Documents</h3>
          <p className="section-subtitle">Upload and process documents for classification</p>
          <input type="file" id="file-input" multiple onChange={handleFileSelection} accept=".pdf,.txt,.doc,.docx" style={{ display: 'none' }} />
          
          <div className="button-spacing-large">
            <div className="file-input-wrapper">
              <label className={`file-label ${selectedFiles && selectedFiles.length > 0 ? 'has-files' : ''}`} htmlFor="file-input-input" onClick={() => setSelectedFiles(null)}>
                {selectedFiles && selectedFiles.length > 0 
                  ? `✓ ${selectedFiles.length} file${selectedFiles.length !== 1 ? 's' : ''} selected` 
                  : '📁 No files selected'}
              </label>
              <input 
                type="file" 
                id="file-input-input"
                multiple 
                onChange={handleFileSelection} 
                accept=".pdf,.txt,.doc,.docx"
                title="Click to browse files"
              />
            </div>
            <button 
              className="btn-load" 
              disabled={processing || !selectedFiles || selectedFiles.length === 0}
              onClick={handleLoadDocuments}
              title="Classify and process selected documents"
            >
              <span className="btn-icon">{processing ? '⏳' : '🔍'}</span>
              <span className="btn-text">{processing ? 'Classifying...' : 'Classify Documents'}</span>
            </button>
          </div>
          
          {selectedFiles && selectedFiles.length > 0 && (
            <div className="selected-files">
              <div className="selected-files-header">
                <strong>✓ {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected</strong>
              </div>
              <ul className="selected-files-list">
                  {Array.from(selectedFiles).map((file: File, idx: number) => (
                  <li key={idx}>
                    <span className="file-icon">📋</span>
                    <span className="file-name">{file.name}</span>
                    <span className="file-size">({(file.size / 1024).toFixed(1)} KB)</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      <div className="results-section">
        <h3>Processing Results</h3>
        {results.length === 0 ? (
          <div className="empty-results">
            <p>No documents processed yet. Upload and process documents to see results here.</p>
          </div>
        ) : (
          <div className="results-list">
              {results.map((result: DocumentResult, index: number) => (
              <div key={index} className="result-item" title={`Classification: ${result.classification}`}>
                <div className="result-header">
                  <strong>{result.document_name}</strong>
                  <span className={`classification ${result.classification.toLowerCase()}`}>
                    {result.classification}
                  </span>
                </div>
                <div className="result-details">
                  <span>Confidence: {(result.confidence * 100).toFixed(1)}%</span>
                  <span>Status: {result.processing_status}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )

  const renderReview = () => (
    <div className="review">
      <h3>🧑‍⚖️ Human Review</h3>
      <p className="section-subtitle">Review and approve documents requiring human judgment</p>
      {reviewQueue.length === 0 ? (
        <div className="empty-state">
          <p>✨ All caught up! No documents pending review.</p>
        </div>
      ) : (
        <div className="review-layout-fixed">
          {/* Left Panel - Document List */}
          <div className="review-sidebar-fixed">
            <div className="sidebar-header">
              <h4>Pending Documents</h4>
              <span className="badge">{reviewQueue.length}</span>
            </div>
            <div className="document-list-fixed">
                {reviewQueue.map((item: any) => (
                <div
                  key={item.id}
                  className={`document-item-enhanced ${selectedReviewDoc?.id === item.id ? 'selected' : ''}`}
                  onClick={() => setSelectedReviewDoc(item)}
                  title={item.document_name}
                >
                  <div className="document-indicator"></div>
                  <div className="document-info">
                    <div className="document-name-fixed">{item.document_name}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Middle Panel - Document Content */}
          <div className="review-content-fixed">
            {selectedReviewDoc ? (
              <div className="content-display-fixed">
                <div className="content-header">
                  <h4>Document Content</h4>
                  <span className="content-size">{selectedReviewDoc.document_content_preview?.length || 0} characters</span>
                </div>
                <div className="content-text-fixed">
                  <div className="document-text">{selectedReviewDoc.document_content_preview}</div>
                </div>
              </div>
            ) : (
              <div className="content-placeholder-fixed">
                <p>👈 Select a document from the left panel to review its content</p>
              </div>
            )}
          </div>

          {/* Right Panel - Decision */}
          <div className="review-panel-fixed">
            {selectedReviewDoc ? (
              <div className="decision-panel-fixed">
                <h4>⚡ Decision</h4>

                <div className="extracted-fields-compact">
                  <div className="field-item-compact">
                    <label>Document:</label>
                    <span title={selectedReviewDoc.document_name}>{selectedReviewDoc.document_name}</span>
                  </div>
                  <div className="field-item-compact">
                    <label>Time:</label>
                    <span>{new Date(selectedReviewDoc.timestamp).toLocaleString()}</span>
                  </div>
                  <div className="field-item-compact">
                    <label>Size:</label>
                    <span>{selectedReviewDoc.document_content_preview?.length || 0} chars</span>
                  </div>
                </div>

                <div className="decision-section-fixed">
                  <label htmlFor="decision-select">Select Outcome:</label>
                  <select id="decision-select" className="decision-dropdown-fixed">
                    <option value="">Choose action...</option>
                    <option value="Cease">✅ Approve - Cease Request</option>
                    <option value="Irrelevant">❌ Reject - Irrelevant Request</option>
                  </select>

                  <div className="decision-actions-fixed">
                    <button
                      className="btn-submit"
                      onClick={() => {
                        const select = document.getElementById('decision-select') as HTMLSelectElement
                        const decision = select.value
                        if (decision) {
                          handleSubmitReview(selectedReviewDoc.document_name, decision)
                          setSelectedReviewDoc(null)
                          select.value = ''
                        } else {
                          setMessage('Please select a decision')
                        }
                      }}
                    >
                      Submit Decision
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="panel-placeholder-fixed">
                <p>👉 Select a document to make a decision</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )

  const renderAudit = () => (
    <div className="audit">
      <h3>📋 Audit Log</h3>
      <p className="section-subtitle">Complete activity history and system events</p>
      <div className="audit-controls">
        <button className="btn-refresh" onClick={() => loadInitialData()} title="Refresh the audit log">
          🔄 Refresh Logs
        </button>
      </div>

      <div className="audit-list">
        {auditLogs.length === 0 ? (
          <p className="empty-audit">No audit entries found</p>
        ) : (
          auditLogs.map((entry, index) => (
            <div key={index} className="audit-entry">
              <div className="audit-header">
                <span className="timestamp" title={entry.timestamp}>{new Date(entry.timestamp).toLocaleString()}</span>
                <span className="agent">{entry.agent_name}</span>
                <span className={`status ${entry.status.toLowerCase()}`}>{entry.status}</span>
              </div>
              <div className="audit-content">
                <div className="action">{entry.action}</div>
                {entry.document_name && <div className="document">📄 {entry.document_name}</div>}
                {entry.classification && <div className="classification">Classification: {entry.classification}</div>}
                {entry.explanation && <div className="explanation">{entry.explanation}</div>}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )

  const renderSettings = () => (
    <div className="settings">
      <h3>⚙️ System Settings</h3>
      <p className="section-subtitle">Configure and manage system functionality</p>

      <div className="settings-section">
        <h4>System Management</h4>
        <div className="setting-item">
          <div className="setting-info">
            <h5>🔄 Reset System</h5>
            <p>Clear all data, logs, and archived documents. This action cannot be undone.</p>
          </div>
          <button
            className={`btn-reset ${showResetConfirm ? 'confirming' : ''}`}
            onClick={handleResetSystem}
            title="Click to reset, click again to confirm"
          >
            {showResetConfirm ? '⚠️ Confirm Reset' : '🗑️ Reset System'}
          </button>
        </div>
      </div>

      <div className="settings-section">
        <h4>System Information</h4>
        <div className="info-grid">
          <div className="info-item">
            <label>Health Status:</label>
            <span className={health === 'ok' ? 'healthy' : 'unhealthy'}>{health === 'ok' ? '✅ Healthy' : '❌ Offline'}</span>
          </div>
          <div className="info-item">
            <label>Total Documents:</label>
            <span>{status?.database_stats?.total_documents ?? 0}</span>
          </div>
          <div className="info-item">
            <label>Archived:</label>
            <span>{status?.archive_stats?.total_archived ?? 0}</span>
          </div>
        </div>
      </div>
    </div>
  )

  return (
    <div className="app-shell container-fluid px-3">
      <header className="app-header card bg-primary text-white mb-3">
        <div className="card-body header-main d-flex align-items-center w-100 position-relative">
          {/* Left: logo */}
          <div className="logo-section d-flex align-items-center gap-2">
            <div className="logo bg-white text-primary rounded px-3 py-2">EDPS</div>
          </div>

          {/* Center: title + tagline */}
          <div className="header-title text-center flex-fill">
            <h1 className="mb-1">Enterprise Document Processing System</h1>
            <small>Intelligent document processing with human review and archiving</small>
          </div>

          {/* Right: compact theme toggle + visible signout button */}
          <div className="theme-toggle-container position-absolute top-0 end-0 p-3 d-flex align-items-center gap-2">
            <div className="theme-toggle btn-group" role="group" aria-label="Theme toggle">
              <button
                className={`btn btn-xs ${theme === 'light' ? 'btn-light active' : 'btn-outline-light'}`}
                onClick={() => handleThemeChange('light')}
                title="Switch to light mode"
                data-tooltip="Switch to light mode"
              >
                ☀️
              </button>
              <button
                className={`btn btn-xs ${theme === 'dark' ? 'btn-light active' : 'btn-outline-light'}`}
                onClick={() => handleThemeChange('dark')}
                title="Switch to dark mode"
                data-tooltip="Switch to dark mode"
              >
                🌙
              </button>
            </div>
            <button
              className="btn btn-signout"
              onClick={handleSignOut}
              title="Logout and stop services"
              data-tooltip="Shutdown backend and close UI"
            >
              🚪
            </button>
          </div>
        </div>
      </header>

      <nav className="app-navigation nav nav-pills flex-wrap gap-2 mb-3">
        <button
          className={`nav-link ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          📊 Dashboard
        </button>
        <button
          className={`nav-link ${activeTab === 'documents' ? 'active' : ''}`}
          onClick={() => setActiveTab('documents')}
        >
          📁 Load Documents
        </button>
        <button
          className={`nav-link ${activeTab === 'review' ? 'active' : ''}`}
          onClick={() => setActiveTab('review')}
        >
          👥 Human Review ({reviewQueue.length})
        </button>
        <button
          className={`nav-link ${activeTab === 'audit' ? 'active' : ''}`}
          onClick={() => setActiveTab('audit')}
        >
          📋 Audit
        </button>
        <button
          className={`nav-link ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          ⚙️ Settings
        </button>
      </nav>

      <main className="app-main">
        {activeTab === 'dashboard' && renderDashboard()}
        {activeTab === 'documents' && renderDocuments()}
        {activeTab === 'review' && renderReview()}
        {activeTab === 'audit' && renderAudit()}
        {activeTab === 'settings' && renderSettings()}
      </main>

      {message && (
        <div className="notification">
          {message}
        </div>
      )}
    </div>
  )
}

export default App
