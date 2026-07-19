import React, { useState, useEffect, useRef } from 'react'
import './App.css'

interface LogFile {
  id: string
  name: string
  filename: string
  type: string
}

interface ConsoleLog {
  timestamp: string
  level: string
  message: string
}

interface StageStatus {
  status: string
  time: number
}

interface RunData {
  run_id: string
  status: string
  log_name: string
  stages: Record<string, StageStatus>
  console_logs: ConsoleLog[]
  report: {
    pipeline_error: string
    failure_type: string
    root_cause: string
    explanation: string
    evidence: string[]
    suggested_fixes: string[]
    original_confidence: number
    final_confidence: number
    critic_status: string
    critic_comments: string
  } | null
  error: string | null
}

function App() {
  const [activeTab, setActiveTab] = useState<'home' | 'dashboard' | 'analysis' | 'architecture'>('home')
  const [logs, setLogs] = useState<LogFile[]>([])
  const [selectedLogId, setSelectedLogId] = useState<string>('')
  const [activeRunId, setActiveRunId] = useState<string>('')
  const [runData, setRunData] = useState<RunData | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  
  const terminalEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Fetch available logs on mount
  useEffect(() => {
    fetchLogs()
  }, [])

  // Auto-scroll terminal when logs change
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [runData?.console_logs])

  // Poll run status when analyzing
  useEffect(() => {
    let intervalId: any
    if (isAnalyzing && activeRunId) {
      intervalId = setInterval(async () => {
        try {
          const res = await fetch(`/api/runs/${activeRunId}`)
          if (!res.ok) throw new Error('Failed to fetch run status')
          const data: RunData = await res.json()
          setRunData(data)
          
          if (data.status === 'completed' || data.status === 'failed') {
            setIsAnalyzing(false)
            if (data.status === 'completed') {
              showToast('Analysis completed successfully!')
              // Navigate to analysis tab automatically
              setTimeout(() => {
                setActiveTab('analysis')
              }, 1500)
            } else {
              showToast('Analysis failed. Check logs.')
            }
          }
        } catch (err) {
          console.error(err)
        }
      }, 1000)
    }
    return () => clearInterval(intervalId)
  }, [isAnalyzing, activeRunId])

  const fetchLogs = async () => {
    try {
      const res = await fetch('/api/logs')
      if (res.ok) {
        const data = await res.json()
        setLogs(data)
        if (data.length > 0) {
          setSelectedLogId(data[0].id)
        }
      }
    } catch (err) {
      console.error('Error fetching logs:', err)
    }
  }

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => {
      setToastMessage(null)
    }, 4000)
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    const file = files[0]
    const formData = new FormData()
    formData.append('file', file)

    setIsUploading(true)
    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) throw new Error('Upload failed')
      const data = await res.json()
      showToast(`Uploaded ${file.name} successfully.`)
      // Refresh logs list and select the uploaded log
      await fetchLogs()
      setSelectedLogId(data.log_id)
    } catch (err: any) {
      showToast(`Upload failed: ${err.message}`)
    } finally {
      setIsUploading(false)
    }
  }

  const startAnalysis = async (logId: string) => {
    if (!logId) return
    setIsAnalyzing(true)
    setRunData(null)
    
    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ log_id: logId })
      })
      if (!res.ok) throw new Error('Analysis request failed')
      const data = await res.json()
      setActiveRunId(data.run_id)
      
      // Fetch initial status
      const runStatusRes = await fetch(`/api/runs/${data.run_id}`)
      if (runStatusRes.ok) {
        setRunData(await runStatusRes.json())
      }
    } catch (err: any) {
      showToast(`Analysis failed to start: ${err.message}`)
      setIsAnalyzing(false)
    }
  }

  const executeFix = async () => {
    if (!activeRunId) return
    try {
      const res = await fetch('/api/fix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: activeRunId, fix_index: 0 })
      })
      if (res.ok) {
        const data = await res.json()
        showToast(data.message)
      }
    } catch (err: any) {
      showToast(`Failed to execute fix: ${err.message}`)
    }
  }

  // Stepper UI helper calculations
  const getStepStatus = (step: 'parsing' | 'classifying' | 'planning' | 'remediation') => {
    if (!runData) return { status: 'PENDING', label: 'Pending', color: 'text-on-surface-variant' }

    const stages = runData.stages
    
    if (step === 'parsing') {
      const s = stages['Parser']
      if (s.status === 'SUCCESS') return { status: 'SUCCESS', label: 'Completed', color: 'text-tertiary' }
      if (s.status === 'RUNNING') return { status: 'RUNNING', label: 'In Progress...', color: 'text-primary' }
      if (s.status === 'FAILED') return { status: 'FAILED', label: 'Failed', color: 'text-error' }
      return { status: 'PENDING', label: 'Pending', color: 'text-on-surface-variant' }
    }

    if (step === 'classifying') {
      const s = stages['Classifier']
      if (s.status === 'SUCCESS') return { status: 'SUCCESS', label: 'Completed', color: 'text-tertiary' }
      if (s.status === 'RUNNING') return { status: 'RUNNING', label: 'In Progress...', color: 'text-primary' }
      if (s.status === 'FAILED') return { status: 'FAILED', label: 'Failed', color: 'text-error' }
      return { status: 'PENDING', label: 'Pending', color: 'text-on-surface-variant' }
    }

    if (step === 'planning') {
      const planningStages = ['Planner', 'Collector', 'Chunker', 'Embedder', 'Vector Store', 'Retriever', 'LLM', 'Critic']
      const statuses = planningStages.map(st => stages[st]?.status || 'PENDING')
      
      if (statuses.includes('FAILED')) return { status: 'FAILED', label: 'Failed', color: 'text-error' }
      if (stages['Critic']?.status === 'SUCCESS') return { status: 'SUCCESS', label: 'Completed', color: 'text-tertiary' }
      if (statuses.includes('RUNNING') || stages['Classifier']?.status === 'SUCCESS') {
        return { status: 'RUNNING', label: 'In Progress...', color: 'text-primary' }
      }
      return { status: 'PENDING', label: 'Pending', color: 'text-on-surface-variant' }
    }

    if (step === 'remediation') {
      const s = stages['Report']
      if (s.status === 'SUCCESS') return { status: 'SUCCESS', label: 'Completed', color: 'text-tertiary' }
      if (s.status === 'RUNNING') return { status: 'RUNNING', label: 'Applying...', color: 'text-primary' }
      if (s.status === 'FAILED') return { status: 'FAILED', label: 'Failed', color: 'text-error' }
      return { status: 'PENDING', label: 'Pending', color: 'text-on-surface-variant' }
    }

    return { status: 'PENDING', label: 'Pending', color: 'text-on-surface-variant' }
  }

  // Custom styling helper for console logs based on levels
  const getLogColor = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR': return 'text-[#ffb4ab]'
      case 'WARNING': return 'text-[#ffbd2e]'
      case 'INFO': return 'text-on-surface'
      case 'DEBUG': return 'text-secondary opacity-75'
      default: return 'text-on-surface'
    }
  }

  return (
    <div className="flex flex-col min-h-screen">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-8 z-[100] bg-surface-container-high border border-primary/30 text-primary px-6 py-4 rounded-xl shadow-2xl animate-pulse flex items-center gap-3">
          <span className="material-symbols-outlined text-[20px]">info</span>
          <span className="font-semibold text-sm">{toastMessage}</span>
        </div>
      )}

      {/* Top Navigation */}
      <nav className="bg-surface-container-low border-b border-outline-variant shadow-sm w-full h-16 sticky top-0 z-50">
        <div className="flex items-center justify-between px-gutter w-full max-w-container-max mx-auto h-full">
          <div className="flex items-center gap-stack-lg">
            <span className="font-headline-sm text-headline-sm font-bold text-primary cursor-pointer active:scale-95" onClick={() => setActiveTab('home')}>
              Nexus.ai
            </span>
            <div className="hidden md:flex items-center gap-stack-md ml-stack-lg">
              <button 
                onClick={() => setActiveTab('home')}
                className={`pb-5 pt-5 font-body-md text-body-md cursor-pointer transition-all active:scale-95 ${activeTab === 'home' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface-variant font-medium hover:text-primary'}`}
              >
                Home
              </button>
              <button 
                onClick={() => setActiveTab('dashboard')}
                className={`pb-5 pt-5 font-body-md text-body-md cursor-pointer transition-all active:scale-95 ${activeTab === 'dashboard' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface-variant font-medium hover:text-primary'}`}
              >
                Dashboard
              </button>
              <button 
                onClick={() => setActiveTab('analysis')}
                className={`pb-5 pt-5 font-body-md text-body-md cursor-pointer transition-all active:scale-95 ${activeTab === 'analysis' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface-variant font-medium hover:text-primary'}`}
              >
                Analysis
              </button>
              <button 
                onClick={() => setActiveTab('architecture')}
                className={`pb-5 pt-5 font-body-md text-body-md cursor-pointer transition-all active:scale-95 ${activeTab === 'architecture' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface-variant font-medium hover:text-primary'}`}
              >
                Architecture
              </button>
            </div>
          </div>
          
          <div className="flex items-center gap-stack-md">
            <div className="relative group hidden lg:block">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">search</span>
              <input 
                className="bg-surface-container-lowest border border-outline-variant rounded-lg pl-10 pr-4 py-1.5 w-64 focus:border-primary focus:ring-1 focus:ring-primary transition-all text-sm outline-none text-on-surface" 
                placeholder="Search telemetry..." 
                type="text"
              />
            </div>
            <div className="flex items-center gap-stack-sm text-on-surface-variant">
              <span className="material-symbols-outlined cursor-pointer hover:text-primary transition-colors p-2 rounded-full hover:bg-surface-variant" onClick={() => setActiveTab('dashboard')}>terminal</span>
              <span className="material-symbols-outlined cursor-pointer hover:text-primary transition-colors p-2 rounded-full hover:bg-surface-variant">settings</span>
              <span className="material-symbols-outlined cursor-pointer hover:text-primary transition-colors p-2 rounded-full hover:bg-surface-variant">help</span>
            </div>
            <button className="bg-primary-container text-on-primary-container px-4 py-1.5 rounded-lg font-semibold text-sm hover:opacity-90 active:scale-95 transition-all">
              Deploy
            </button>
            <div className="w-8 h-8 rounded-full bg-surface-container-highest flex items-center justify-center overflow-hidden border border-outline-variant">
              <span className="material-symbols-outlined text-[20px] text-primary">account_circle</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content Areas */}
      <main className="flex-grow w-full">
        
        {/* 1. HOME TAB */}
        {activeTab === 'home' && (
          <section className="relative pt-12 pb-24 px-gutter max-w-container-max mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-stack-xl items-center mt-8">
              <div className="z-10">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary font-label-md text-label-md mb-stack-md">
                  <span className="material-symbols-outlined text-[14px]" style={{ fontVariationSettings: "'FILL' 1" }}>auto_awesome</span>
                  <span>V2.4 Active Monitoring Enabled</span>
                </div>
                <h1 className="font-headline-lg text-[56px] leading-[1.1] mb-stack-lg tracking-tight font-bold">
                  AI-Powered CI/CD Pipeline <br/>
                  <span className="text-primary">Failure Investigation</span>
                </h1>
                <p className="text-on-surface-variant font-body-lg text-body-lg max-w-xl mb-stack-xl leading-relaxed">
                  Nexus.ai autonomously triages, investigates, and proposes fixes for pipeline failures. By combining Agentic RAG with deep log telemetry, we reduce MTTR from hours to seconds.
                </p>
                <div className="flex flex-wrap gap-stack-md mt-6">
                  <button 
                    onClick={() => setActiveTab('dashboard')}
                    className="bg-[#5B8CFF] text-white px-8 py-4 rounded-xl font-bold flex items-center gap-2 shadow-[0_4px_20px_rgba(91,140,255,0.4)] hover:scale-[1.02] active:scale-95 transition-all cursor-pointer"
                  >
                    <span>Analyze Logs</span>
                    <span className="material-symbols-outlined">arrow_forward</span>
                  </button>
                  <button 
                    onClick={() => setActiveTab('architecture')}
                    className="glass-card px-8 py-4 rounded-xl font-bold flex items-center gap-2 hover:bg-surface-container-highest transition-all cursor-pointer"
                  >
                    <span>View Architecture</span>
                  </button>
                </div>
              </div>

              {/* Pipeline Visualization */}
              <div className="relative group">
                <div className="absolute inset-0 bg-primary/5 rounded-[40px] blur-3xl group-hover:bg-primary/10 transition-all duration-700"></div>
                <div className="glass-card rounded-[32px] p-stack-lg relative border-primary/20 overflow-hidden min-h-[440px] flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-stack-sm">
                      <div className="w-3 h-3 rounded-full bg-error animate-pulse"></div>
                      <span className="font-label-md text-label-md text-error">Pipeline Status: Failed</span>
                    </div>
                    <span className="font-label-sm text-label-sm text-on-surface-variant">Active Monitor</span>
                  </div>

                  <div className="flex-grow flex flex-col justify-center gap-6 my-4">
                    <div className="flex justify-center">
                      <div className="pipeline-node glass-card px-4 py-3 rounded-xl border-dashed flex flex-col items-center gap-1 w-40">
                        <span className="material-symbols-outlined text-on-surface-variant">source</span>
                        <span className="font-label-sm text-label-sm">GitHub Push Trigger</span>
                      </div>
                    </div>
                    <div className="flex justify-center relative">
                      <div className="absolute h-10 w-0.5 bg-gradient-to-b from-outline-variant to-primary -top-8"></div>
                      <div className="pipeline-node bg-surface-container-highest border border-primary/50 px-6 py-4 rounded-xl flex flex-col items-center gap-1 w-56 shadow-lg shadow-primary/10">
                        <div className="flex items-center gap-2">
                          <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>robot_2</span>
                          <span className="font-label-md text-label-md font-bold text-primary">AGENTIC RAG</span>
                        </div>
                        <div className="w-full bg-surface-dim h-1 rounded-full mt-2 overflow-hidden">
                          <div className="bg-primary h-full w-2/3 animate-pulse"></div>
                        </div>
                      </div>
                      <div className="absolute h-10 w-0.5 bg-gradient-to-b from-primary to-outline-variant -bottom-8"></div>
                    </div>
                    <div className="flex justify-between items-center gap-4">
                      <div className="pipeline-node glass-card p-4 rounded-xl flex-1 flex flex-col gap-2 border-primary/10">
                        <span className="text-primary font-label-sm text-label-sm font-semibold">KNOWLEDGE BASE</span>
                        <div className="flex gap-1">
                          <div className="h-1 flex-1 bg-primary/30 rounded"></div>
                          <div className="h-1 flex-1 bg-primary/30 rounded"></div>
                          <div className="h-1 flex-1 bg-primary/10 rounded"></div>
                        </div>
                      </div>
                      <div className="pipeline-node glass-card p-4 rounded-xl flex-1 flex flex-col gap-2 border-secondary/20">
                        <span className="text-secondary font-label-sm text-label-sm font-semibold">LOG CONTEXT</span>
                        <div className="flex gap-1">
                          <div className="h-1 flex-1 bg-secondary/30 rounded"></div>
                          <div className="h-1 flex-1 bg-secondary/10 rounded"></div>
                          <div className="h-1 flex-1 bg-secondary/30 rounded"></div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="glass-card p-4 rounded-xl terminal-panel border-error/20">
                    <div className="flex items-center gap-2 mb-1.5">
                      <div className="w-2 h-2 rounded-full bg-error"></div>
                      <span className="text-[10px] text-error uppercase font-bold tracking-widest">Triage Engine</span>
                    </div>
                    <p className="text-xs text-on-surface-variant font-mono italic leading-relaxed">
                      &gt; Scan repositories ... build failures detected. Select logs on Dashboard to execute analysis.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Engineering Pillars Section */}
            <div className="mt-20">
              <div className="mb-8">
                <h2 className="font-headline-md text-headline-md text-on-surface font-semibold">Core Engineering Pillars</h2>
                <p className="text-on-surface-variant font-body-md text-body-md mt-1">The architectural foundation of our high-precision debugging engine.</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-stack-lg">
                <div className="group glass-card p-stack-lg rounded-[20px] border-outline-variant hover:border-primary/40 transition-all duration-300">
                  <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary mb-stack-md group-hover:scale-110 transition-transform">
                    <span className="material-symbols-outlined text-[28px]">rebase_edit</span>
                  </div>
                  <h3 className="font-headline-sm text-headline-sm mb-stack-sm font-semibold">Log Parsing</h3>
                  <p className="text-on-surface-variant font-body-md text-body-md leading-relaxed mb-stack-md">
                    Proprietary ingestion engine that normalizes unstructured logs from K8s, GitHub runners, and logs files into structured error contexts.
                  </p>
                </div>
                <div className="group glass-card p-stack-lg rounded-[20px] border-outline-variant hover:border-secondary/40 transition-all duration-300">
                  <div className="w-12 h-12 rounded-xl bg-secondary/10 flex items-center justify-center text-secondary mb-stack-md group-hover:scale-110 transition-transform">
                    <span className="material-symbols-outlined text-[28px]">search_insights</span>
                  </div>
                  <h3 className="font-headline-sm text-headline-sm mb-stack-sm font-semibold">Semantic Retrieval</h3>
                  <p className="text-on-surface-variant font-body-md text-body-md leading-relaxed mb-stack-md">
                    Beyond simple keywords. We use dense embedding context searches to match exceptions against historical documentation and issues.
                  </p>
                </div>
                <div className="group glass-card p-stack-lg rounded-[20px] border-outline-variant hover:border-tertiary/40 transition-all duration-300">
                  <div className="w-12 h-12 rounded-xl bg-tertiary/10 flex items-center justify-center text-tertiary mb-stack-md group-hover:scale-110 transition-transform">
                    <span className="material-symbols-outlined text-[28px]">fact_check</span>
                  </div>
                  <h3 className="font-headline-sm text-headline-sm mb-stack-sm font-semibold">Critic Agent</h3>
                  <p className="text-on-surface-variant font-body-md text-body-md leading-relaxed mb-stack-md">
                    Our rule-based critic validates proposed fixes against repository policies to eliminate hallucinations and verify grounding.
                  </p>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* 2. DASHBOARD TAB */}
        {activeTab === 'dashboard' && (
          <section className="max-w-container-max mx-auto px-gutter py-8 flex flex-col gap-6">
            
            {/* Top Grid: Drop Zone + Stepper */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter items-stretch">
              
              {/* Left Column: Drop logs & selection */}
              <div className="lg:col-span-4 flex flex-col gap-4">
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileUpload} 
                  className="hidden" 
                  accept=".txt,.log,.zip"
                />
                
                {/* Drag-n-Drop Zone */}
                <div 
                  onClick={() => fileInputRef.current?.click()}
                  className="glass-panel rounded-xl p-6 flex flex-col items-center justify-center text-center border-2 border-dashed border-outline-variant hover:border-primary transition-all group cursor-pointer h-60 relative overflow-hidden"
                >
                  {isUploading ? (
                    <div className="flex flex-col items-center">
                      <span className="material-symbols-outlined text-primary text-5xl animate-spin">sync</span>
                      <h3 className="font-headline-sm text-headline-sm text-on-surface mt-4">Uploading log...</h3>
                    </div>
                  ) : (
                    <div className="relative z-10 flex flex-col items-center">
                      <div className="w-16 h-16 bg-surface-container rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                        <span className="material-symbols-outlined text-primary text-4xl" style={{ fontVariationSettings: "'FILL' 1" }}>upload_file</span>
                      </div>
                      <h2 className="font-headline-sm text-headline-sm text-on-surface font-semibold mb-1.5">Drop debug logs here</h2>
                      <p className="text-on-surface-variant text-body-md mb-4 text-xs">Or click to browse .TXT, .LOG, or .ZIP</p>
                    </div>
                  )}
                </div>

                {/* Predefined Logs List */}
                <div className="glass-panel rounded-xl p-4 flex-grow flex flex-col gap-2.5">
                  <h3 className="font-label-md text-label-md text-on-surface-variant border-b border-outline-variant pb-2">CHOOSE LOG FILE</h3>
                  <div className="flex flex-col gap-2 overflow-y-auto max-h-48 pr-1">
                    {logs.map((log) => (
                      <button
                        key={log.id}
                        onClick={() => setSelectedLogId(log.id)}
                        className={`w-full text-left p-3 rounded-lg border text-xs flex items-center justify-between transition-all cursor-pointer ${selectedLogId === log.id ? 'border-primary bg-primary/10 text-primary font-bold' : 'border-outline-variant bg-surface-container-lowest/50 hover:bg-surface-container-high'}`}
                      >
                        <span className="truncate pr-2">{log.name}</span>
                        <span className="text-[10px] uppercase font-mono px-2 py-0.5 bg-surface-container-highest rounded text-on-surface-variant shrink-0">{log.type}</span>
                      </button>
                    ))}
                  </div>
                  <button
                    onClick={() => startAnalysis(selectedLogId)}
                    disabled={isAnalyzing || !selectedLogId}
                    className="w-full bg-primary text-on-primary py-3 rounded-lg font-bold hover:opacity-90 active:scale-95 transition-all text-sm mt-2 flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                  >
                    {isAnalyzing ? (
                      <>
                        <span className="material-symbols-outlined text-sm animate-spin">refresh</span>
                        Analyzing Pipeline...
                      </>
                    ) : (
                      <>
                        <span className="material-symbols-outlined text-sm">play_arrow</span>
                        Run Analysis
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Right Column: Stepper Progression */}
              <div className="lg:col-span-8">
                <div className="glass-panel rounded-xl p-6 h-full flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                      <span className="material-symbols-outlined text-secondary">analytics</span>
                      <h2 className="font-headline-sm text-headline-sm text-on-surface font-semibold">Pipeline Execution</h2>
                    </div>
                    {runData && (
                      <div className="flex items-center gap-3">
                        <span className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-label-md border ${runData.status === 'running' ? 'bg-primary/15 text-primary border-primary/25' : runData.status === 'completed' ? 'bg-tertiary/15 text-tertiary border-tertiary/25' : 'bg-error/15 text-error border-error/25'}`}>
                          <span className={`w-2 h-2 rounded-full ${runData.status === 'running' ? 'bg-primary animate-pulse' : runData.status === 'completed' ? 'bg-tertiary' : 'bg-error'}`}></span> 
                          {runData.status.toUpperCase()}
                        </span>
                        <span className="text-on-surface-variant text-label-md font-mono text-xs">ID: {runData.run_id.substring(0, 8)}...</span>
                      </div>
                    )}
                  </div>

                  <div className="flex-grow flex flex-col justify-around py-4">
                    <div className="relative flex flex-col gap-6 pl-10">
                      
                      {/* Central vertical line */}
                      <div className="absolute left-[15px] top-4 bottom-4 w-0.5 bg-outline-variant"></div>
                      
                      {/* Step 1: Parsing */}
                      {(() => {
                        const step = getStepStatus('parsing')
                        return (
                          <div className="flex items-start gap-4 relative z-10">
                            <div className={`absolute left-[-25px] w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${step.status === 'SUCCESS' ? 'bg-tertiary text-on-tertiary' : step.status === 'RUNNING' ? 'bg-primary text-on-primary active-step-glow animate-pulse' : step.status === 'FAILED' ? 'bg-error text-on-error' : 'bg-surface-container-highest text-on-surface-variant'}`}>
                              {step.status === 'SUCCESS' ? <span className="material-symbols-outlined text-sm">check</span> : '1'}
                            </div>
                            <div className="flex-grow grid grid-cols-2">
                              <div>
                                <h3 className={`font-body-lg text-body-lg font-semibold ${step.color}`}>Parsing</h3>
                                <p className="text-on-surface-variant text-xs mt-0.5">Ingesting log stream and isolating exception traces</p>
                              </div>
                              <div className="text-right">
                                <p className="text-on-surface-variant font-mono text-[10px]">{runData?.stages['Parser']?.time ? `${runData.stages['Parser'].time.toFixed(2)}s` : '--'}</p>
                                <p className={`font-semibold text-xs ${step.color}`}>{step.label}</p>
                              </div>
                            </div>
                          </div>
                        )
                      })()}

                      {/* Step 2: Classifying */}
                      {(() => {
                        const step = getStepStatus('classifying')
                        return (
                          <div className="flex items-start gap-4 relative z-10">
                            <div className={`absolute left-[-25px] w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${step.status === 'SUCCESS' ? 'bg-tertiary text-on-tertiary' : step.status === 'RUNNING' ? 'bg-primary text-on-primary active-step-glow animate-pulse' : step.status === 'FAILED' ? 'bg-error text-on-error' : 'bg-surface-container-highest text-on-surface-variant'}`}>
                              {step.status === 'SUCCESS' ? <span className="material-symbols-outlined text-sm">check</span> : '2'}
                            </div>
                            <div className="flex-grow grid grid-cols-2">
                              <div>
                                <h3 className={`font-body-lg text-body-lg font-semibold ${step.color}`}>Classifying</h3>
                                <p className="text-on-surface-variant text-xs mt-0.5">Mapping exceptions to known failure modules</p>
                              </div>
                              <div className="text-right">
                                <p className="text-on-surface-variant font-mono text-[10px]">{runData?.stages['Classifier']?.time ? `${runData.stages['Classifier'].time.toFixed(2)}s` : '--'}</p>
                                <p className={`font-semibold text-xs ${step.color}`}>{step.label}</p>
                              </div>
                            </div>
                          </div>
                        )
                      })()}

                      {/* Step 3: Planning & RAG */}
                      {(() => {
                        const step = getStepStatus('planning')
                        return (
                          <div className="flex items-start gap-4 relative z-10">
                            <div className={`absolute left-[-25px] w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${step.status === 'SUCCESS' ? 'bg-tertiary text-on-tertiary' : step.status === 'RUNNING' ? 'bg-primary text-on-primary active-step-glow animate-pulse' : step.status === 'FAILED' ? 'bg-error text-on-error' : 'bg-surface-container-highest text-on-surface-variant'}`}>
                              {step.status === 'SUCCESS' ? <span className="material-symbols-outlined text-sm">check</span> : '3'}
                            </div>
                            <div className="flex-grow grid grid-cols-2">
                              <div>
                                <h3 className={`font-body-lg text-body-lg font-semibold ${step.color}`}>Planning & Retrieval</h3>
                                <p className="text-on-surface-variant text-xs mt-0.5">RAG search context creation, database query, and Gemini analysis</p>
                              </div>
                              <div className="text-right">
                                <p className="text-on-surface-variant font-mono text-[10px]">
                                  {(() => {
                                    if (!runData) return '--'
                                    const t = ['Planner', 'Collector', 'Chunker', 'Embedder', 'Vector Store', 'Retriever', 'LLM', 'Critic']
                                      .reduce((acc, st) => acc + (runData.stages[st]?.time || 0), 0)
                                    return t > 0 ? `${t.toFixed(2)}s` : '--'
                                  })()}
                                </p>
                                <p className={`font-semibold text-xs ${step.color}`}>{step.label}</p>
                              </div>
                            </div>
                          </div>
                        )
                      })()}

                      {/* Step 4: Remediation Report */}
                      {(() => {
                        const step = getStepStatus('remediation')
                        return (
                          <div className="flex items-start gap-4 relative z-10">
                            <div className={`absolute left-[-25px] w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${step.status === 'SUCCESS' ? 'bg-tertiary text-on-tertiary' : step.status === 'RUNNING' ? 'bg-primary text-on-primary active-step-glow animate-pulse' : step.status === 'FAILED' ? 'bg-error text-on-error' : 'bg-surface-container-highest text-on-surface-variant'}`}>
                              {step.status === 'SUCCESS' ? <span className="material-symbols-outlined text-sm">check</span> : '4'}
                            </div>
                            <div className="flex-grow grid grid-cols-2">
                              <div>
                                <h3 className={`font-body-lg text-body-lg font-semibold ${step.color}`}>Remediation</h3>
                                <p className="text-on-surface-variant text-xs mt-0.5">Critic compliance checks and final report generation</p>
                              </div>
                              <div className="text-right">
                                <p className="text-on-surface-variant font-mono text-[10px]">{runData?.stages['Report']?.time ? `${runData.stages['Report'].time.toFixed(2)}s` : '--'}</p>
                                <p className={`font-semibold text-xs ${step.color}`}>{step.label}</p>
                              </div>
                            </div>
                          </div>
                        )
                      })()}

                    </div>
                  </div>
                </div>
              </div>
              
            </div>

            {/* Bottom Row: Console Logger Terminal */}
            <div className="flex flex-col h-72">
              <div className="bg-[#050810] border border-outline-variant rounded-xl overflow-hidden flex flex-col h-full shadow-2xl">
                <div className="bg-surface-container-high px-4 py-2 flex items-center justify-between border-b border-outline-variant shrink-0">
                  <div className="flex items-center gap-3">
                    <div className="flex gap-1.5">
                      <div className="w-3 h-3 rounded-full bg-[#ff5f56]"></div>
                      <div className="w-3 h-3 rounded-full bg-[#ffbd2e]"></div>
                      <div className="w-3 h-3 rounded-full bg-[#27c93f]"></div>
                    </div>
                    <span className="font-label-md text-label-md text-on-surface-variant ml-2 uppercase tracking-widest text-xs">System Logger Terminal — telemetry.sh</span>
                  </div>
                  <div className="flex items-center gap-4 text-xs">
                    <span className="text-on-surface-variant flex items-center gap-1">
                      <span className="material-symbols-outlined text-sm">filter_list</span> All Streams
                    </span>
                    <button 
                      onClick={() => {
                        if (runData?.console_logs) {
                          const text = runData.console_logs.map(l => `[${l.timestamp}] [${l.level}] ${l.message}`).join('\n')
                          navigator.clipboard.writeText(text)
                          showToast('Logs copied to clipboard!')
                        }
                      }}
                      className="text-on-surface-variant hover:text-primary transition-colors cursor-pointer"
                    >
                      <span className="material-symbols-outlined text-sm">content_copy</span>
                    </button>
                  </div>
                </div>
                
                <div className="flex-grow p-4 font-mono text-xs terminal-scroll overflow-y-auto leading-relaxed space-y-1 select-text">
                  {!runData || runData.console_logs.length === 0 ? (
                    <div className="text-on-surface-variant/40 italic">Waiting for analysis run execution...</div>
                  ) : (
                    runData.console_logs.map((log, idx) => (
                      <div key={idx} className="flex gap-4">
                        <span className="text-outline shrink-0">{log.timestamp}</span>
                        <span className={`shrink-0 font-semibold [width:60px]`}>[{log.level}]</span>
                        <span className={getLogColor(log.level)}>{log.message}</span>
                      </div>
                    ))
                  )}
                  <div ref={terminalEndRef} />
                </div>
              </div>
            </div>

          </section>
        )}

        {/* 3. ANALYSIS TAB */}
        {activeTab === 'analysis' && (
          <section className="max-w-container-max mx-auto px-gutter py-8 overflow-hidden h-[calc(100vh-64px)] flex flex-col gap-6">
            {!runData || !runData.report ? (
              <div className="flex-grow flex flex-col items-center justify-center text-center">
                <span className="material-symbols-outlined text-primary text-6xl animate-pulse">report_off</span>
                <h2 className="font-headline-md text-headline-md text-on-surface mt-4 font-semibold">No Active Report Available</h2>
                <p className="text-on-surface-variant text-body-md mt-2 max-w-sm">Please navigate to the Dashboard and run an analysis on a log file first.</p>
                <button 
                  onClick={() => setActiveTab('dashboard')} 
                  className="bg-primary text-on-primary px-6 py-2.5 rounded-lg font-bold text-sm mt-4 active:scale-95 transition-all cursor-pointer"
                >
                  Go to Dashboard
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter h-full overflow-hidden items-stretch">
                
                {/* Left Column: Failure Report */}
                <div className="col-span-12 lg:col-span-4 flex flex-col overflow-hidden h-full">
                  <div className="glass p-6 rounded-xl flex flex-col gap-4 relative h-full justify-between">
                    <div>
                      <span className="text-error font-label-sm uppercase tracking-widest flex items-center gap-1.5 mb-1.5 text-xs font-semibold">
                        <span className="material-symbols-outlined text-[14px]">error</span> Critical Failure Identified
                      </span>
                      <h1 className="font-headline-md text-headline-md text-on-surface leading-tight font-bold border-b border-outline-variant pb-2">
                        {runData.report.failure_type}
                      </h1>
                      <div className="bg-surface-container-low p-4 rounded-lg border border-error/20 mt-4">
                        <h3 className="text-on-surface font-semibold text-sm">Root Cause</h3>
                        <p className="text-on-surface-variant text-xs mt-1 leading-relaxed">{runData.report.root_cause}</p>
                      </div>
                      <div className="bg-surface-container-low p-4 rounded-lg border border-outline-variant mt-4">
                        <h3 className="text-on-surface font-semibold text-sm">Detailed Explanation</h3>
                        <p className="text-on-surface-variant text-xs mt-1 leading-relaxed max-h-48 overflow-y-auto pr-1">{runData.report.explanation}</p>
                      </div>
                    </div>

                    <div className="flex flex-col gap-4 mt-4 shrink-0">
                      <div className="flex flex-col items-center py-4 gap-2 bg-surface-container-lowest/50 rounded-lg border border-outline-variant">
                        <div className="relative w-24 h-24 flex items-center justify-center">
                          {/* Circular progress simulated */}
                          <svg className="w-full h-full transform -rotate-90">
                            <circle cx="48" cy="48" r="40" stroke="var(--outline-variant)" strokeWidth="4" fill="transparent" />
                            <circle 
                              cx="48" 
                              cy="48" 
                              r="40" 
                              stroke="var(--primary)" 
                              strokeWidth="4" 
                              fill="transparent" 
                              strokeDasharray={2 * Math.PI * 40}
                              strokeDashoffset={2 * Math.PI * 40 * (1 - runData.report.final_confidence / 100)}
                            />
                          </svg>
                          <div className="absolute flex flex-col items-center">
                            <span className="font-headline-md text-headline-md text-primary font-bold">{runData.report.final_confidence}%</span>
                            <span className="text-[8px] font-bold text-on-surface-variant tracking-wider">CONFIDENCE</span>
                          </div>
                        </div>
                        <p className="text-xs text-tertiary font-semibold">
                          {runData.report.final_confidence > 75 ? 'High Confidence Match' : runData.report.final_confidence > 50 ? 'Moderate Match' : 'Uncertain Match'}
                        </p>
                      </div>

                      <button 
                        onClick={executeFix}
                        className="w-full bg-[#5B8CFF] text-white py-3 rounded-lg font-bold flex items-center justify-center gap-2 hover:scale-[1.01] active:scale-95 transition-all text-sm pulse-ai cursor-pointer shadow-[0_0_15px_rgba(91,140,255,0.3)]"
                      >
                        <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>auto_fix</span>
                        Execute Automated Fix
                      </button>
                    </div>
                  </div>
                </div>

                {/* Middle Column: Evidence */}
                <div className="col-span-12 lg:col-span-4 flex flex-col gap-4 overflow-hidden h-full">
                  <div className="flex justify-between items-center shrink-0">
                    <h2 className="font-headline-sm text-headline-sm font-semibold">Supporting Evidence</h2>
                    <span className="bg-surface-container-high px-2 py-0.5 rounded text-xs text-on-surface-variant font-semibold">
                      {runData.report.evidence.length} Cited
                    </span>
                  </div>
                  
                  <div className="flex-grow flex flex-col gap-3 overflow-y-auto terminal-scroll pr-1 pb-4">
                    {runData.report.evidence.map((ev, idx) => (
                      <div key={idx} className="glass p-4 rounded-xl hover:bg-surface-container-highest transition-all group border border-outline-variant">
                        <div className="flex justify-between items-center mb-2">
                          <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-primary text-lg">description</span>
                            <span className="font-label-md text-on-surface font-semibold text-xs truncate max-w-[200px]">{ev.split(' (Source:')[0]}</span>
                          </div>
                          <span className="text-[10px] text-tertiary font-mono bg-tertiary/10 border border-tertiary/20 px-2 py-0.5 rounded">RAG Evidence #{idx+1}</span>
                        </div>
                        <div className="bg-[#050810] p-3 rounded border border-outline-variant/50 font-mono text-[11px] text-on-surface-variant group-hover:border-primary/50 transition-colors whitespace-pre-wrap leading-relaxed">
                          {ev.includes('Source:') ? `Source metadata: ${ev.split('Source:')[1].replace(')', '')}` : 'Referenced document segment verified and matched by Vector Index.'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Right Column: Critic */}
                <div className="col-span-12 lg:col-span-4 flex flex-col overflow-hidden h-full">
                  <div className="glass h-full p-6 rounded-xl flex flex-col border-t-2 border-t-tertiary justify-between">
                    <div>
                      <div className="flex items-center gap-3 mb-6 border-b border-outline-variant pb-4">
                        <div className="w-10 h-10 rounded-full bg-tertiary/10 flex items-center justify-center">
                          <span className="material-symbols-outlined text-tertiary">verified_user</span>
                        </div>
                        <div>
                          <h2 className="font-headline-sm text-headline-sm font-semibold">Critic Agent</h2>
                          <span className="text-xs text-on-surface-variant">Validation Protocol v2.4</span>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <div className="bg-tertiary/10 border border-tertiary/20 rounded-xl p-6 text-center">
                          <span className="material-symbols-outlined text-[48px] text-tertiary block mb-2" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
                          <div className="text-lg font-bold text-tertiary uppercase tracking-wider">{runData.report.critic_status}</div>
                          <p className="text-on-surface-variant text-xs mt-1">Cross-referenced against local validation rules</p>
                        </div>
                        
                        <div className="space-y-3">
                          <h3 className="font-label-md text-on-surface-variant border-b border-outline-variant pb-1 text-xs uppercase tracking-wider font-semibold">Verification Audit Notes</h3>
                          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                            {runData.report.critic_comments.split(' | ').map((note, index) => (
                              <div key={index} className="flex gap-2 items-start text-xs text-on-surface-variant leading-relaxed">
                                <span className="material-symbols-outlined text-tertiary text-sm mt-0.5">check</span>
                                <p>{note}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="pt-4 border-t border-outline-variant flex items-center justify-between text-xs mt-4">
                      <span className="font-label-sm text-on-surface-variant italic">Agent ID: Nexus-Critic-01</span>
                      <button className="text-primary font-bold hover:underline cursor-pointer">View Logic Chain</button>
                    </div>
                  </div>
                </div>

              </div>
            )}
          </section>
        )}

        {/* 4. ARCHITECTURE TAB */}
        {activeTab === 'architecture' && (
          <section className="max-w-container-max mx-auto px-gutter py-8 flex flex-col gap-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="font-headline-lg text-headline-lg text-on-background font-bold">Inference Pipeline <span className="text-primary">V2.4.0</span></h1>
                <p className="font-body-md text-body-md text-on-surface-variant mt-0.5">Real-time architectural trace and node synchronization status.</p>
              </div>
              <div className="bg-surface-container-high px-3 py-1.5 rounded-lg flex items-center gap-2 border border-outline-variant text-xs">
                <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span>
                <span className="font-semibold text-tertiary">Live System Logs</span>
              </div>
            </div>

            {/* Architecture Node SVG Map */}
            <div className="relative w-full h-[360px] glass-panel rounded-xl overflow-hidden flex items-center justify-center">
              
              {/* Connector lines SVG */}
              <svg className="absolute inset-0 w-full h-full pointer-events-none hidden md:block" xmlns="http://www.w3.org/2000/svg">
                <line x1="12%" y1="50%" x2="25%" y2="50%" stroke="var(--color-primary, #5b8cff)" strokeWidth="1" strokeDasharray="4" className="node-connector" />
                <line x1="33%" y1="50%" x2="48%" y2="50%" stroke="var(--color-primary, #5b8cff)" strokeWidth="1" strokeDasharray="4" className="node-connector" />
                
                {/* Branch split */}
                <path d="M 56% 50% Q 62% 50% 68% 28%" fill="none" stroke="var(--color-primary, #5b8cff)" strokeWidth="1" strokeDasharray="4" className="node-connector" />
                <path d="M 56% 50% Q 62% 50% 68% 72%" fill="none" stroke="var(--color-primary, #5b8cff)" strokeWidth="1" strokeDasharray="4" className="node-connector" />
                
                {/* Branch merge */}
                <path d="M 76% 28% Q 82% 50% 88% 50%" fill="none" stroke="var(--color-primary, #5b8cff)" strokeWidth="1" strokeDasharray="4" className="node-connector" />
                <path d="M 76% 72% Q 82% 50% 88% 50%" fill="none" stroke="var(--color-primary, #5b8cff)" strokeWidth="1" strokeDasharray="4" className="node-connector" />
              </svg>
              
              {/* Node Layout Grid */}
              <div className="relative z-10 flex flex-wrap md:flex-nowrap justify-center md:justify-between items-center w-full px-8 gap-8">
                
                {/* Node 1: Push Trigger */}
                <div className="pipeline-node flex flex-col items-center gap-2">
                  <div className="w-12 h-12 bg-surface-container-highest rounded-xl flex items-center justify-center border border-primary/20 node-glow">
                    <span className="material-symbols-outlined text-primary text-xl">art_track</span>
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-xs text-on-surface">GitHub Webhook</p>
                    <p className="text-[10px] text-on-surface-variant opacity-60">Source Trigger</p>
                  </div>
                </div>

                {/* Node 2: Parser */}
                <div className="pipeline-node flex flex-col items-center gap-2">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center border ${runData?.stages['Parser']?.status === 'SUCCESS' ? 'bg-tertiary/10 border-tertiary text-tertiary' : 'bg-surface-container-highest border-primary/20 text-secondary'}`}>
                    <span className="material-symbols-outlined text-xl">data_object</span>
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-xs text-on-surface">Log Parser</p>
                    <p className="text-[10px] text-on-surface-variant opacity-60">AST Mapping</p>
                  </div>
                </div>

                {/* Node 3: Planner */}
                <div className="pipeline-node flex flex-col items-center gap-2">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center border ${runData?.stages['Planner']?.status === 'SUCCESS' ? 'bg-tertiary/10 border-tertiary text-tertiary' : 'bg-surface-container-highest border-primary/20 text-tertiary'}`}>
                    <span className="material-symbols-outlined text-xl">account_tree</span>
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-xs text-on-surface">Planner Agent</p>
                    <p className="text-[10px] text-on-surface-variant opacity-60">Search Strategy</p>
                  </div>
                </div>

                {/* Split Column */}
                <div className="flex flex-col gap-6">
                  {/* Node 4A: Vector DB */}
                  <div className="pipeline-node flex flex-col items-center gap-2">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center border ${runData?.stages['Vector Store']?.status === 'SUCCESS' ? 'bg-tertiary/10 border-tertiary text-tertiary' : 'bg-surface-container-highest border-primary/20 text-primary'}`}>
                      <span className="material-symbols-outlined text-xl">database</span>
                    </div>
                    <div className="text-center">
                      <p className="font-semibold text-xs text-on-surface">FAISS Vector DB</p>
                      <p className="text-[10px] text-on-surface-variant opacity-60">Dense Embeddings</p>
                    </div>
                  </div>
                  
                  {/* Node 4B: Gemini inference */}
                  <div className="pipeline-node flex flex-col items-center gap-2">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${runData?.stages['LLM']?.status === 'SUCCESS' ? 'bg-tertiary text-on-tertiary' : 'bg-primary text-on-primary shadow-lg shadow-primary/25 animate-pulse'}`}>
                      <span className="material-symbols-outlined text-xl">smart_toy</span>
                    </div>
                    <div className="text-center">
                      <p className="font-semibold text-xs text-on-surface">Gemini Pro</p>
                      <p className="text-[10px] text-on-surface-variant opacity-60">Inference Core</p>
                    </div>
                  </div>
                </div>

                {/* Node 5: Critic */}
                <div className="pipeline-node flex flex-col items-center gap-2">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center border ${runData?.stages['Critic']?.status === 'SUCCESS' ? 'bg-tertiary/10 border-tertiary text-tertiary' : runData?.stages['Critic']?.status === 'RUNNING' ? 'border-primary/60 text-primary' : 'bg-surface-container-highest border-error/20 text-error'}`}>
                    <span className="material-symbols-outlined text-xl">fact_check</span>
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-xs text-on-surface">Critic validation</p>
                    <p className="text-[10px] text-on-surface-variant opacity-60">Compliance check</p>
                  </div>
                </div>

                {/* Node 6: Final Report */}
                <div className="pipeline-node flex flex-col items-center gap-2">
                  <div className={`w-14 h-14 rounded-full flex items-center justify-center border-2 ${runData?.stages['Report']?.status === 'SUCCESS' ? 'bg-tertiary/25 border-tertiary text-tertiary' : 'bg-surface-container-highest border-outline text-on-surface-variant'}`}>
                    <span className="material-symbols-outlined text-2xl">description</span>
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-xs text-on-surface">Remediation Fix</p>
                    <p className="text-[10px] text-on-surface-variant opacity-60">Report output</p>
                  </div>
                </div>

              </div>
            </div>

            {/* System Health Info cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-stretch">
              <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant flex flex-col justify-between">
                <div>
                  <span className="text-on-surface-variant text-xs font-semibold block mb-1">Average Latency</span>
                  <span className="text-2xl font-bold text-primary font-mono">184ms</span>
                </div>
                <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden mt-3">
                  <div className="h-full bg-primary" style={{ width: '24%' }}></div>
                </div>
                <span className="text-[9px] font-mono text-outline mt-2 uppercase">Nominal Operating range</span>
              </div>
              
              <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant flex flex-col justify-between">
                <div>
                  <span className="text-on-surface-variant text-xs font-semibold block mb-1">Token Efficiency</span>
                  <span className="text-2xl font-bold text-tertiary font-mono">92.4%</span>
                </div>
                <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden mt-3">
                  <div className="h-full bg-tertiary" style={{ width: '92%' }}></div>
                </div>
                <span className="text-[9px] font-mono text-outline mt-2 uppercase">Optimized for Gemini context</span>
              </div>

              <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant flex flex-col justify-between">
                <div>
                  <span className="text-on-surface-variant text-xs font-semibold block mb-1">GPU Cluster Load</span>
                  <span className="text-2xl font-bold text-secondary font-mono">68%</span>
                </div>
                <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden mt-3">
                  <div className="h-full bg-secondary" style={{ width: '68%' }}></div>
                </div>
                <span className="text-[9px] font-mono text-outline mt-2 uppercase">H100 status: normal</span>
              </div>

              <div className="bg-surface-container-lowest p-5 rounded-xl border border-outline-variant flex flex-col justify-between">
                <div>
                  <span className="text-on-surface-variant text-xs font-semibold block mb-1">Active Queue Jobs</span>
                  <span className="text-2xl font-bold text-on-surface font-mono">0</span>
                </div>
                <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden mt-3">
                  <div className="h-full bg-outline" style={{ width: '0%' }}></div>
                </div>
                <span className="text-[9px] font-mono text-outline mt-2 uppercase">All tasks synchronized</span>
              </div>
            </div>
          </section>
        )}

      </main>

      {/* Footer bar */}
      <footer className="bg-surface-container-lowest border-t border-outline-variant w-full py-4 text-xs mt-auto">
        <div className="flex flex-col md:flex-row justify-between items-center px-gutter w-full max-w-container-max mx-auto gap-2">
          <div className="flex flex-col gap-0.5">
            <span className="font-semibold text-on-surface-variant uppercase tracking-wider text-[10px]">Nexus AI Platform</span>
            <p className="text-secondary">© 2024 Nexus AI Platform. System Status: All Systems Operational.</p>
          </div>
          <div className="flex gap-4">
            <a className="text-on-surface-variant hover:text-tertiary transition-colors underline-offset-4 hover:underline" href="#">Documentation</a>
            <a className="text-on-surface-variant hover:text-tertiary transition-colors underline-offset-4 hover:underline" href="#">API Reference</a>
            <a className="text-on-surface-variant hover:text-tertiary transition-colors underline-offset-4 hover:underline" href="#">Changelog</a>
            <a className="text-on-surface-variant hover:text-tertiary transition-colors underline-offset-4 hover:underline" href="#">Privacy Policy</a>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
