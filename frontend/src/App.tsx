import React, { useState, useEffect, useRef } from 'react'
import './App.css'

const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

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
    is_recurring?: boolean
    recurrence_count?: number
    error_signature?: string
    intelligence_note?: string
    failure_category?: string
    severity_score?: number
    severity_tier?: string
    blast_radius?: string
    remediation_id?: string
    code_patch?: {
      patch_id: string
      title: string
      target_file: string
      diff_content: string
      rationale: string
      risk_level: string
      validation_command: string
      status: string
    }
    past_occurrences?: Array<{
      run_id: string
      commit_sha: string
      branch: string
      timestamp: string
      workflow_name: string
      root_cause: string
      suggested_fixes: string[]
    }>
  } | null
  error: string | null
}

interface Repository {
  id: string
  owner: string
  name: string
  full_name: string
  is_private: boolean
  default_branch: string
  webhook_secret: string
  is_active: boolean
  member_count: number
  runs_count: number
  last_failure_at: string | null
}

interface PipelineEvent {
  id: string
  repo_full_name: string
  github_run_id: string
  workflow_name: string
  branch: string
  commit_sha: string
  commit_message: string
  status: string
  conclusion: string
  created_at: string
  analysis?: {
    failure_type: string
    root_cause: string
    explanation: string
    confidence: number
    suggested_fixes: string[]
    critic_status: string
    analysis_run_id: string
    is_recurring?: boolean
    recurrence_count?: number
  } | null
}

interface InAppNotificationItem {
  id: string
  user_id: string
  username: string
  repo_name: string
  run_id?: string
  title: string
  message: string
  severity: string
  event_type: string
  is_read: boolean
  created_at: string
}

interface NotificationPreference {
  email_enabled: boolean
  slack_enabled: boolean
  discord_enabled: boolean
  in_app_enabled: boolean
  notify_critical_only: boolean
}

interface NotificationChannel {
  id: string
  channel: string
  target: string
  is_active: boolean
  created_at: string
}

interface SystemStatus {
  status: string
  version: string
  database: {
    dialect: string
    status: string
    pool_size?: number
    overflow?: number
  }
  queue: {
    configured_mode: string
    active_mode: string
    redis_connected: boolean
    task_acks_late: boolean
    prefetch_multiplier: number
  }
}

function App() {
  const [activeTab, setActiveTab] = useState<'home' | 'repositories' | 'monitoring' | 'dashboard' | 'analysis' | 'architecture'>('home')
  const [logs, setLogs] = useState<LogFile[]>([])
  const [selectedLogId, setSelectedLogId] = useState<string>('')
  const [activeRunId, setActiveRunId] = useState<string>('')
  const [runData, setRunData] = useState<RunData | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  // Milestone 1 (Repositories & RBAC) State
  const [repos, setRepos] = useState<Repository[]>([])
  const [repoUrlInput, setRepoUrlInput] = useState('')
  const [repoTokenInput, setRepoTokenInput] = useState('')
  const [repoSecretInput, setRepoSecretInput] = useState('')
  const [isConnectingRepo, setIsConnectingRepo] = useState(false)
  const [lastConnectedRole, setLastConnectedRole] = useState<{ gh_perm: string; app_role: string } | null>(null)

  // Milestone 2 (Webhooks & Failure Detection) State
  const [pipelineEvents, setPipelineEvents] = useState<PipelineEvent[]>([])
  const [isSimulatingWebhook, setIsSimulatingWebhook] = useState(false)
  const [simRepo, setSimRepo] = useState('')
  const [simWorkflow, setSimWorkflow] = useState('Backend CI Pipeline')
  const [simBranch, setSimBranch] = useState('main')
  const [simCommitMsg, setSimCommitMsg] = useState('fix: update checkout session handler')

  // Milestone 3 (Notification Engine & Preferences) State
  const [notifications, setNotifications] = useState<InAppNotificationItem[]>([])
  const [unreadCount, setUnreadCount] = useState<number>(0)
  const [isNotificationOpen, setIsNotificationOpen] = useState<boolean>(false)
  const [preferences, setPreferences] = useState<NotificationPreference>({
    email_enabled: true,
    slack_enabled: true,
    discord_enabled: true,
    in_app_enabled: true,
    notify_critical_only: false
  })
  const [channels, setChannels] = useState<NotificationChannel[]>([])
  const [newChannelType, setNewChannelType] = useState('slack')
  const [newChannelTarget, setNewChannelTarget] = useState('')

  // Milestone 4 (System Telemetry) State
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)

  const terminalEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const notifDropdownRef = useRef<HTMLDivElement>(null)

  // Fetch initial telemetry
  useEffect(() => {
    fetchLogs()
    fetchRepositories()
    fetchPipelineEvents()
    fetchNotifications()
    fetchPreferences()
    fetchSystemStatus()
  }, [])

  // Close notifications dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (notifDropdownRef.current && !notifDropdownRef.current.contains(event.target as Node)) {
        setIsNotificationOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
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
          const res = await fetch(`${API_BASE}/api/runs/${activeRunId}`)
          if (!res.ok) throw new Error('Failed to fetch run status')
          const data: RunData = await res.json()
          setRunData(data)
          
          if (data.status === 'completed' || data.status === 'failed') {
            setIsAnalyzing(false)
            fetchPipelineEvents()
            fetchRepositories()
            fetchNotifications()
            if (data.status === 'completed') {
              showToast('Analysis completed successfully!')
              setTimeout(() => {
                setActiveTab('analysis')
              }, 1200)
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
      const res = await fetch(`${API_BASE}/api/logs`)
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

  const fetchRepositories = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/repos`)
      if (res.ok) {
        const data = await res.json()
        setRepos(data)
        if (data.length > 0 && !simRepo) {
          setSimRepo(data[0].full_name)
          fetchRepoChannels(data[0].id)
        }
      }
    } catch (err) {
      console.error('Error fetching repos:', err)
    }
  }

  const fetchPipelineEvents = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/events`)
      if (res.ok) {
        const data = await res.json()
        setPipelineEvents(data)
      }
    } catch (err) {
      console.error('Error fetching events:', err)
    }
  }

  const fetchNotifications = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/notifications`)
      if (res.ok) {
        const data = await res.json()
        setNotifications(data.notifications)
        setUnreadCount(data.unread_count)
      }
    } catch (err) {
      console.error('Error fetching notifications:', err)
    }
  }

  const fetchPreferences = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/notifications/preferences`)
      if (res.ok) {
        const data = await res.json()
        setPreferences(data)
      }
    } catch (err) {
      console.error('Error fetching preferences:', err)
    }
  }

  const fetchSystemStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/system/status`)
      if (res.ok) {
        const data = await res.json()
        setSystemStatus(data)
      }
    } catch (err) {
      console.error('Error fetching system status:', err)
    }
  }

  const updatePreferenceToggle = async (key: keyof NotificationPreference, val: boolean) => {
    const updated = { ...preferences, [key]: val }
    setPreferences(updated)
    try {
      await fetch(`${API_BASE}/api/notifications/preferences`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated)
      })
      showToast('Notification preference updated.')
    } catch (err) {
      console.error('Error updating preference:', err)
    }
  }

  const fetchRepoChannels = async (repoId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/repos/${repoId}/notifications`)
      if (res.ok) {
        const data = await res.json()
        setChannels(data)
      }
    } catch (err) {
      console.error('Error fetching channels:', err)
    }
  }

  const handleAddChannel = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newChannelTarget.trim()) return
    const targetRepo = repos.find(r => r.full_name === simRepo) || repos[0]
    if (!targetRepo) return

    try {
      const res = await fetch(`${API_BASE}/api/repos/${targetRepo.id}/notifications`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          channel: newChannelType,
          target_url_or_email: newChannelTarget.trim()
        })
      })
      if (res.ok) {
        showToast(`${newChannelType.toUpperCase()} alert channel registered!`)
        setNewChannelTarget('')
        fetchRepoChannels(targetRepo.id)
      }
    } catch (err: any) {
      showToast(`Error adding channel: ${err.message}`)
    }
  }

  const markNotificationRead = async (id: string) => {
    try {
      await fetch(`${API_BASE}/api/notifications/${id}/read`, { method: 'PATCH' })
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n))
      setUnreadCount(prev => Math.max(0, prev - 1))
    } catch (err) {
      console.error('Error marking read:', err)
    }
  }

  const markAllNotificationsRead = async () => {
    try {
      await fetch(`${API_BASE}/api/notifications/mark-all-read`, { method: 'POST' })
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
      setUnreadCount(0)
      showToast('All notifications marked as read.')
    } catch (err) {
      console.error('Error marking all read:', err)
    }
  }

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => {
      setToastMessage(null)
    }, 4500)
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Upload failed')
      }

      const uploaded = await res.json()
      showToast(`Log file "${file.name}" uploaded successfully`)
      await fetchLogs()
      setSelectedLogId(uploaded.log_id)
    } catch (err: any) {
      showToast(err.message)
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const startAnalysis = async (logId: string) => {
    if (!logId) return
    setIsAnalyzing(true)
    setActiveTab('dashboard')
    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ log_id: logId }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to trigger analysis')
      }
      const data = await res.json()
      setActiveRunId(data.run_id)
      showToast('Pipeline investigation initialized...')
    } catch (err: any) {
      showToast(`Analysis failed to start: ${err.message}`)
      setIsAnalyzing(false)
    }
  }

  const handleConnectRepo = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!repoUrlInput.trim()) {
      showToast('Please enter a GitHub repository URL or slug')
      return
    }

    setIsConnectingRepo(true)
    try {
      const res = await fetch(`${API_BASE}/api/repos/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: repoUrlInput.trim(),
          token: repoTokenInput.trim() || undefined,
          webhook_secret: repoSecretInput.trim() || undefined
        })
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to connect repository')
      }

      const data = await res.json()
      showToast(`Repository ${data.repository.full_name} connected! Assigned Role: ${data.permissions.app_role}`)
      setLastConnectedRole({
        gh_perm: data.permissions.github_permission,
        app_role: data.permissions.app_role
      })
      setRepoUrlInput('')
      setRepoTokenInput('')
      setRepoSecretInput('')
      await fetchRepositories()
    } catch (err: any) {
      showToast(`Connection failed: ${err.message}`)
    } finally {
      setIsConnectingRepo(false)
    }
  }

  const handleSimulateWebhook = async () => {
    setIsSimulatingWebhook(true)
    try {
      const res = await fetch(`${API_BASE}/api/webhooks/github/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_full_name: simRepo || undefined,
          workflow_name: simWorkflow,
          branch: simBranch,
          commit_sha: 'a82f91c',
          commit_message: simCommitMsg,
          error_type: 'AssertionError: Expected 200, got 500'
        })
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Simulation failed')
      }

      const data = await res.json()
      showToast(`Webhook validated! AI diagnosis & role-based notifications dispatched.`)
      
      if (data.run_id) {
        setActiveRunId(data.run_id)
        setIsAnalyzing(true)
        setActiveTab('dashboard')
      }
      await fetchPipelineEvents()
      await fetchNotifications()
    } catch (err: any) {
      showToast(`Simulation error: ${err.message}`)
    } finally {
      setIsSimulatingWebhook(false)
    }
  }

  const executeFix = async () => {
    if (!activeRunId) return
    try {
      const res = await fetch(`${API_BASE}/api/fix`, {
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

  const handleReviewPatch = async (action: 'approve' | 'reject') => {
    const patchId = runData?.report?.code_patch?.patch_id || runData?.report?.remediation_id
    if (!patchId) return
    try {
      const res = await fetch(`${API_BASE}/api/remediations/${patchId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action,
          reviewer_role: 'Developer',
          reviewer_username: 'developer-oncall',
          comment: `Human review: ${action}d from interactive dashboard.`
        })
      })
      if (res.ok) {
        const data = await res.json()
        showToast(data.message)
        if (runData?.report?.code_patch) {
          setRunData({
            ...runData,
            report: {
              ...runData.report,
              code_patch: { ...runData.report.code_patch, status: data.status }
            }
          })
        }
      } else {
        const err = await res.json()
        showToast(err.detail || 'Review failed.')
      }
    } catch (err: any) {
      showToast(`Review error: ${err.message}`)
    }
  }

  const handleApplyPatch = async () => {
    const patchId = runData?.report?.code_patch?.patch_id || runData?.report?.remediation_id
    if (!patchId) return
    try {
      const res = await fetch(`${API_BASE}/api/remediations/${patchId}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'apply' })
      })
      if (res.ok) {
        const data = await res.json()
        showToast(data.message)
        if (runData?.report?.code_patch) {
          setRunData({
            ...runData,
            report: {
              ...runData.report,
              code_patch: { ...runData.report.code_patch, status: 'applied' }
            }
          })
        }
      } else {
        const err = await res.json()
        showToast(err.detail || 'Failed to apply patch.')
      }
    } catch (err: any) {
      showToast(`Apply error: ${err.message}`)
    }
  }

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
            <span className="font-headline-sm text-headline-sm font-bold text-primary cursor-pointer active:scale-95 flex items-center gap-2" onClick={() => setActiveTab('home')}>
              <span className="material-symbols-outlined text-primary text-2xl">troubleshoot</span>
              Pipeline Failure 3.0
            </span>
            <div className="hidden md:flex items-center gap-stack-md ml-stack-lg">
              <button 
                onClick={() => setActiveTab('home')}
                className={`pb-5 pt-5 font-body-md text-body-md cursor-pointer transition-all active:scale-95 ${activeTab === 'home' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface-variant font-medium hover:text-primary'}`}
              >
                Home
              </button>
              <button 
                onClick={() => setActiveTab('repositories')}
                className={`pb-5 pt-5 font-body-md text-body-md cursor-pointer transition-all active:scale-95 ${activeTab === 'repositories' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface-variant font-medium hover:text-primary'}`}
              >
                Repositories & Alerts
              </button>
              <button 
                onClick={() => setActiveTab('monitoring')}
                className={`pb-5 pt-5 font-body-md text-body-md cursor-pointer transition-all active:scale-95 ${activeTab === 'monitoring' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface-variant font-medium hover:text-primary'}`}
              >
                Pipeline Monitor (Webhooks)
              </button>
              <button 
                onClick={() => setActiveTab('dashboard')}
                className={`pb-5 pt-5 font-body-md text-body-md cursor-pointer transition-all active:scale-95 ${activeTab === 'dashboard' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface-variant font-medium hover:text-primary'}`}
              >
                Live Analysis
              </button>
              <button 
                onClick={() => setActiveTab('analysis')}
                className={`pb-5 pt-5 font-body-md text-body-md cursor-pointer transition-all active:scale-95 ${activeTab === 'analysis' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface-variant font-medium hover:text-primary'}`}
              >
                Root Cause Report
              </button>
              <button 
                onClick={() => setActiveTab('architecture')}
                className={`pb-5 pt-5 font-body-md text-body-md cursor-pointer transition-all active:scale-95 ${activeTab === 'architecture' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface-variant font-medium hover:text-primary'}`}
              >
                Architecture
              </button>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* System Infrastructure Telemetry Pill */}
            <div className="hidden lg:flex items-center gap-2 px-3 py-1 bg-surface-container rounded-full border border-outline-variant text-[11px] font-mono shadow-sm">
              <span className={`w-2 h-2 rounded-full ${systemStatus?.status === 'online' ? 'bg-emerald-400' : 'bg-amber-400'} animate-pulse`}></span>
              <span className="text-on-surface-variant">
                DB: <span className="text-primary font-semibold">{systemStatus?.database?.dialect === 'postgresql' ? 'PostgreSQL' : 'SQLite Local'}</span>
              </span>
              <span className="text-outline-variant/60">|</span>
              <span className="text-on-surface-variant">
                Queue: <span className="text-secondary font-semibold">{systemStatus?.queue?.active_mode === 'celery' ? 'Celery (Redis)' : 'Local Async'}</span>
              </span>
            </div>

            {/* In-App Notification Bell */}
            <div className="relative" ref={notifDropdownRef}>
              <button
                onClick={() => setIsNotificationOpen(!isNotificationOpen)}
                className="relative p-2 rounded-full hover:bg-surface-container-highest transition-colors cursor-pointer text-on-surface-variant hover:text-primary flex items-center justify-center"
                title="In-App Notifications"
              >
                <span className="material-symbols-outlined text-[22px]">notifications</span>
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 w-4 h-4 bg-error text-white font-mono text-[9px] font-bold rounded-full flex items-center justify-center animate-pulse">
                    {unreadCount}
                  </span>
                )}
              </button>

              {/* Notification Dropdown Drawer */}
              {isNotificationOpen && (
                <div className="absolute right-0 mt-2 w-80 md:w-96 glass-panel rounded-2xl shadow-2xl border border-outline-variant p-4 z-50 flex flex-col gap-3">
                  <div className="flex items-center justify-between border-b border-outline-variant/60 pb-2.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-on-surface">Notifications</span>
                      {unreadCount > 0 && (
                        <span className="px-2 py-0.5 rounded-full bg-error/15 text-error text-[10px] font-bold">
                          {unreadCount} unread
                        </span>
                      )}
                    </div>
                    {unreadCount > 0 && (
                      <button
                        onClick={markAllNotificationsRead}
                        className="text-[11px] text-primary hover:underline font-semibold cursor-pointer"
                      >
                        Mark all read
                      </button>
                    )}
                  </div>

                  <div className="flex flex-col gap-2 max-h-80 overflow-y-auto pr-1">
                    {notifications.length === 0 ? (
                      <div className="py-8 text-center text-on-surface-variant opacity-60 text-xs">
                        No notifications yet.
                      </div>
                    ) : (
                      notifications.map(n => (
                        <div
                          key={n.id}
                          onClick={() => {
                            if (!n.is_read) markNotificationRead(n.id)
                            if (n.run_id) {
                              setActiveTab('monitoring')
                            }
                            setIsNotificationOpen(false)
                          }}
                          className={`p-3 rounded-xl border text-xs flex flex-col gap-1.5 transition-all cursor-pointer ${n.is_read ? 'bg-surface-container-lowest/50 border-outline-variant/40 opacity-70' : 'bg-surface-container-high border-primary/30 shadow-sm'}`}
                        >
                          <div className="flex items-center justify-between">
                            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${n.severity === 'critical' ? 'bg-error/15 text-error' : n.severity === 'warning' ? 'bg-[#ffbd2e]/15 text-[#ffbd2e]' : 'bg-primary/15 text-primary'}`}>
                              {n.event_type.replace('_', ' ')}
                            </span>
                            <span className="text-[10px] font-mono text-on-surface-variant">
                              {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                          <p className="font-bold text-on-surface text-xs leading-snug">{n.title}</p>
                          <p className="text-on-surface-variant text-[11px] line-clamp-2 leading-relaxed">{n.message}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            <span className="px-3 py-1 bg-primary/10 border border-primary/20 text-primary text-xs rounded-full font-mono">
              v3.0 Engine Active
            </span>
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
                  <span className="material-symbols-outlined text-[14px]">bolt</span>
                  <span>Pipeline Failure Detection 3.0 (Role-Aware & Historical Memory)</span>
                </div>
                <h1 className="font-headline-lg text-[52px] leading-[1.15] mb-stack-lg tracking-tight font-bold">
                  Intelligent CI Failure Alerts <br/>
                  <span className="text-primary">& Historical Similarity Memory</span>
                </h1>
                <p className="text-on-surface-variant font-body-lg text-body-lg max-w-xl mb-stack-xl leading-relaxed">
                  Connect repositories, listen for GitHub Actions webhooks, and let the AI correlate errors against persistent failure memory. Alerts are throttled and dynamically routed to Owners, Admins, or Developers based on branch criticality and recurrence.
                </p>
                <div className="flex flex-wrap gap-stack-md mt-6">
                  <button 
                    onClick={() => setActiveTab('repositories')}
                    className="bg-[#5B8CFF] text-white px-7 py-3.5 rounded-xl font-bold flex items-center gap-2 shadow-[0_4px_20px_rgba(91,140,255,0.4)] hover:scale-[1.02] active:scale-95 transition-all cursor-pointer"
                  >
                    <span className="material-symbols-outlined">notifications_active</span>
                    <span>Manage Repos & Alerts</span>
                  </button>
                  <button 
                    onClick={() => setActiveTab('monitoring')}
                    className="glass-card px-7 py-3.5 rounded-xl font-bold flex items-center gap-2 hover:bg-surface-container-highest transition-all cursor-pointer border border-primary/30 text-primary"
                  >
                    <span className="material-symbols-outlined">radar</span>
                    <span>Webhook Monitor & Simulator</span>
                  </button>
                  <button 
                    onClick={() => setActiveTab('dashboard')}
                    className="glass-card px-6 py-3.5 rounded-xl font-semibold flex items-center gap-2 hover:bg-surface-container-highest transition-all cursor-pointer text-on-surface-variant"
                  >
                    <span>Manual Analyzer</span>
                  </button>
                </div>
              </div>

              {/* Status Overview Card */}
              <div className="relative group">
                <div className="absolute inset-0 bg-primary/5 rounded-[40px] blur-3xl group-hover:bg-primary/10 transition-all duration-700"></div>
                <div className="glass-card rounded-[32px] p-stack-lg relative border-primary/20 overflow-hidden min-h-[440px] flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-tertiary animate-pulse"></div>
                      <span className="font-label-md text-label-md text-tertiary">3.0 Notification Engine Active</span>
                    </div>
                    <span className="font-mono text-xs text-on-surface-variant">Alert Deduplication Enabled</span>
                  </div>

                  <div className="flex-grow flex flex-col justify-center gap-4 my-3">
                    <div className="bg-surface-container-lowest/80 border border-outline-variant p-4 rounded-xl flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-primary">notifications</span>
                        <div>
                          <p className="font-bold text-sm text-on-surface">In-App Notifications</p>
                          <p className="text-xs text-on-surface-variant">{unreadCount} unread alerts</p>
                        </div>
                      </div>
                      <span className="font-mono font-bold text-lg text-primary">{notifications.length}</span>
                    </div>

                    <div className="bg-surface-container-lowest/80 border border-outline-variant p-4 rounded-xl flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-error">history</span>
                        <div>
                          <p className="font-bold text-sm text-on-surface">Historical Failure Memory</p>
                          <p className="text-xs text-on-surface-variant">Persistent recurrence tracking</p>
                        </div>
                      </div>
                      <span className="font-mono text-xs px-2.5 py-1 bg-tertiary/15 text-tertiary rounded-full font-semibold">Active</span>
                    </div>

                    <div className="bg-surface-container-lowest/80 border border-outline-variant p-4 rounded-xl flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-secondary">alt_route</span>
                        <div>
                          <p className="font-bold text-sm text-on-surface">Role-Based Routing</p>
                          <p className="text-xs text-on-surface-variant">Main $\rightarrow$ Devs+Admin, Recurrent $\rightarrow$ Owner</p>
                        </div>
                      </div>
                      <span className="font-mono text-xs px-2.5 py-1 bg-secondary/15 text-secondary rounded-full font-semibold">Enforced</span>
                    </div>
                  </div>

                  <div className="glass-card p-4 rounded-xl terminal-panel border-primary/20">
                    <div className="flex items-center gap-2 mb-1.5">
                      <div className="w-2 h-2 rounded-full bg-primary animate-ping"></div>
                      <span className="text-[10px] text-primary uppercase font-bold tracking-widest">Automatic Failure Ingestion & Alerts</span>
                    </div>
                    <p className="text-xs text-on-surface-variant font-mono leading-relaxed">
                      GitHub Actions &gt; Webhook Ingestion &gt; Historical Signature Check &gt; Gemini &gt; Critic &gt; Role-Aware Alert Dispatch
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* 2. REPOSITORIES & ALERTS TAB (Milestone 1 & 3) */}
        {activeTab === 'repositories' && (
          <section className="max-w-container-max mx-auto px-gutter py-8 flex flex-col gap-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-on-surface">Repositories, Access & Notification Routing</h2>
                <p className="text-sm text-on-surface-variant">Connect repositories, configure role-based alert policies, and register external notification webhooks.</p>
              </div>
            </div>

            {/* Connect Repository Card */}
            <div className="glass-panel p-6 rounded-2xl border border-outline-variant">
              <h3 className="text-base font-bold text-primary flex items-center gap-2 mb-4">
                <span className="material-symbols-outlined">add_link</span>
                Connect New GitHub Repository
              </h3>
              <form onSubmit={handleConnectRepo} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                <div className="flex flex-col gap-1.5 md:col-span-1">
                  <label className="text-xs font-semibold text-on-surface-variant">Repository URL or Slug *</label>
                  <input 
                    type="text" 
                    value={repoUrlInput}
                    onChange={(e) => setRepoUrlInput(e.target.value)}
                    placeholder="https://github.com/owner/repo or owner/repo"
                    className="bg-surface-container-lowest border border-outline-variant rounded-lg px-3.5 py-2 text-sm text-on-surface outline-none focus:border-primary"
                    required
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-on-surface-variant">GitHub Personal Access Token (Optional)</label>
                  <input 
                    type="password" 
                    value={repoTokenInput}
                    onChange={(e) => setRepoTokenInput(e.target.value)}
                    placeholder="ghp_... (needed for private repos or write perms)"
                    className="bg-surface-container-lowest border border-outline-variant rounded-lg px-3.5 py-2 text-sm text-on-surface outline-none focus:border-primary"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-on-surface-variant">Webhook Secret (Optional)</label>
                  <input 
                    type="text" 
                    value={repoSecretInput}
                    onChange={(e) => setRepoSecretInput(e.target.value)}
                    placeholder="Auto-generated if left blank"
                    className="bg-surface-container-lowest border border-outline-variant rounded-lg px-3.5 py-2 text-sm text-on-surface outline-none focus:border-primary"
                  />
                </div>
                <div className="md:col-span-3 flex justify-end gap-3 mt-2">
                  <button
                    type="submit"
                    disabled={isConnectingRepo}
                    className="bg-primary text-on-primary px-6 py-2.5 rounded-lg font-bold text-sm hover:opacity-90 active:scale-95 transition-all flex items-center gap-2 disabled:opacity-50 cursor-pointer"
                  >
                    {isConnectingRepo ? (
                      <>
                        <span className="material-symbols-outlined text-sm animate-spin">refresh</span>
                        Verifying Permissions...
                      </>
                    ) : (
                      <>
                        <span className="material-symbols-outlined text-sm">check_circle</span>
                        Verify & Connect Repository
                      </>
                    )}
                  </button>
                </div>
              </form>

              {lastConnectedRole && (
                <div className="mt-4 p-4 rounded-xl bg-tertiary/10 border border-tertiary/20 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-tertiary">verified_user</span>
                    <div>
                      <p className="text-xs font-bold text-tertiary">Access Verified Successfully</p>
                      <p className="text-xs text-on-surface-variant">
                        GitHub Permission: <span className="font-mono font-bold text-on-surface">{lastConnectedRole.gh_perm.toUpperCase()}</span> → Assigned Application Role: <span className="font-mono font-bold text-primary">{lastConnectedRole.app_role}</span>
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Notification Preferences & Channels Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Notification Preferences Card */}
              <div className="lg:col-span-6 glass-panel p-6 rounded-2xl border border-outline-variant flex flex-col justify-between">
                <div>
                  <h3 className="text-base font-bold text-on-surface flex items-center gap-2 mb-2">
                    <span className="material-symbols-outlined text-primary">tune</span>
                    User Notification Preferences
                  </h3>
                  <p className="text-xs text-on-surface-variant mb-4">
                    Control which channels notify you when build failures occur:
                  </p>
                  
                  <div className="flex flex-col gap-3">
                    <div className="flex items-center justify-between p-3 rounded-xl bg-surface-container-lowest border border-outline-variant/60">
                      <div>
                        <span className="font-semibold text-xs text-on-surface block">In-App Notifications</span>
                        <span className="text-[11px] text-on-surface-variant">Show alerts in notification bell and tray</span>
                      </div>
                      <input 
                        type="checkbox"
                        checked={preferences.in_app_enabled}
                        onChange={(e) => updatePreferenceToggle('in_app_enabled', e.target.checked)}
                        className="w-4 h-4 text-primary rounded cursor-pointer"
                      />
                    </div>

                    <div className="flex items-center justify-between p-3 rounded-xl bg-surface-container-lowest border border-outline-variant/60">
                      <div>
                        <span className="font-semibold text-xs text-on-surface block">Slack Webhook Alerts</span>
                        <span className="text-[11px] text-on-surface-variant">Deliver Block Kit diagnosis to connected Slack channel</span>
                      </div>
                      <input 
                        type="checkbox"
                        checked={preferences.slack_enabled}
                        onChange={(e) => updatePreferenceToggle('slack_enabled', e.target.checked)}
                        className="w-4 h-4 text-primary rounded cursor-pointer"
                      />
                    </div>

                    <div className="flex items-center justify-between p-3 rounded-xl bg-surface-container-lowest border border-outline-variant/60">
                      <div>
                        <span className="font-semibold text-xs text-on-surface block">Critical Failures Only</span>
                        <span className="text-[11px] text-on-surface-variant">Notify only for main branch or recurring failures</span>
                      </div>
                      <input 
                        type="checkbox"
                        checked={preferences.notify_critical_only}
                        onChange={(e) => updatePreferenceToggle('notify_critical_only', e.target.checked)}
                        className="w-4 h-4 text-primary rounded cursor-pointer"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Add External Alert Channel Card */}
              <div className="lg:col-span-6 glass-panel p-6 rounded-2xl border border-outline-variant flex flex-col justify-between">
                <div>
                  <h3 className="text-base font-bold text-on-surface flex items-center gap-2 mb-2">
                    <span className="material-symbols-outlined text-secondary">send</span>
                    Register Alert Channel
                  </h3>
                  <p className="text-xs text-on-surface-variant mb-4">
                    Send failure reports and actionable fixes directly to Slack or Discord:
                  </p>

                  <form onSubmit={handleAddChannel} className="flex flex-col gap-3">
                    <div className="flex gap-3">
                      <select
                        value={newChannelType}
                        onChange={(e) => setNewChannelType(e.target.value)}
                        className="bg-surface-container-lowest border border-outline-variant rounded-lg px-3 py-2 text-xs text-on-surface outline-none"
                      >
                        <option value="slack">Slack Webhook</option>
                        <option value="discord">Discord Webhook</option>
                        <option value="email">Email</option>
                      </select>
                      <input 
                        type="text"
                        value={newChannelTarget}
                        onChange={(e) => setNewChannelTarget(e.target.value)}
                        placeholder="https://hooks.slack.com/services/... or email"
                        className="flex-grow bg-surface-container-lowest border border-outline-variant rounded-lg px-3 py-2 text-xs text-on-surface outline-none focus:border-primary"
                        required
                      />
                    </div>
                    <button
                      type="submit"
                      className="bg-secondary text-on-secondary px-5 py-2.5 rounded-lg font-bold text-xs hover:opacity-90 active:scale-95 transition-all self-end cursor-pointer"
                    >
                      Add Channel
                    </button>
                  </form>
                </div>

                <div className="mt-4 pt-3 border-t border-outline-variant/60">
                  <span className="text-[11px] text-on-surface-variant font-mono">
                    Active Channels for selected repository: {channels.length}
                  </span>
                </div>
              </div>
            </div>

            {/* Role-Based Routing Matrix Reference */}
            <div className="glass-panel p-6 rounded-2xl border border-outline-variant">
              <h3 className="text-base font-bold text-on-surface mb-2 flex items-center gap-2">
                <span className="material-symbols-outlined text-secondary">alt_route</span>
                Role-Based Alert Routing Policy
              </h3>
              <p className="text-xs text-on-surface-variant mb-4">
                Alerts are dispatched to team members based on their application role and failure severity:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
                <div className="bg-surface-container-lowest p-4 rounded-xl border border-error/30">
                  <span className="text-[10px] uppercase font-bold text-error block mb-1">CRITICAL EVENT</span>
                  <h4 className="font-bold text-sm mb-1">Main Branch Failure</h4>
                  <p className="text-on-surface-variant text-[11px]">Routed to: <span className="font-semibold text-primary">Admin + Developers + Owner</span></p>
                </div>
                <div className="bg-surface-container-lowest p-4 rounded-xl border border-error/30">
                  <span className="text-[10px] uppercase font-bold text-error block mb-1">REPEATED EVENT</span>
                  <h4 className="font-bold text-sm mb-1">Recurrent Failure</h4>
                  <p className="text-on-surface-variant text-[11px]">Routed to: <span className="font-semibold text-primary">Owner + Admin</span> (Escalated)</p>
                </div>
                <div className="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant">
                  <span className="text-[10px] uppercase font-bold text-[#ffbd2e] block mb-1">WARNING EVENT</span>
                  <h4 className="font-bold text-sm mb-1">Feature Branch Failure</h4>
                  <p className="text-on-surface-variant text-[11px]">Routed to: <span className="font-semibold text-primary">Assigned Developer</span></p>
                </div>
                <div className="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant">
                  <span className="text-[10px] uppercase font-bold text-primary block mb-1">GOVERNANCE</span>
                  <h4 className="font-bold text-sm mb-1">Repo Access Change</h4>
                  <p className="text-on-surface-variant text-[11px]">Routed to: <span className="font-semibold text-primary">Repository Owner</span></p>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* 3. PIPELINE MONITOR (WEBHOOKS) TAB */}
        {activeTab === 'monitoring' && (
          <section className="max-w-container-max mx-auto px-gutter py-8 flex flex-col gap-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-on-surface">Automatic Pipeline Failure Detection</h2>
                <p className="text-sm text-on-surface-variant">Continuous monitoring of GitHub Actions workflow executions via HMAC-verified webhooks.</p>
              </div>
            </div>

            {/* Webhook Configuration & Simulator Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              
              {/* Webhook Listener Details */}
              <div className="lg:col-span-5 glass-panel p-6 rounded-2xl border border-outline-variant flex flex-col justify-between">
                <div>
                  <h3 className="text-base font-bold text-primary flex items-center gap-2 mb-3">
                    <span className="material-symbols-outlined">satellite_alt</span>
                    Webhook Listener Specification
                  </h3>
                  <p className="text-xs text-on-surface-variant leading-relaxed mb-4">
                    GitHub Actions notifies this endpoint on completion. If conclusion is <code className="text-error font-mono">failure</code>, AI diagnosis and role-based alerts are triggered.
                  </p>
                  
                  <div className="flex flex-col gap-3">
                    <div className="bg-surface-container-lowest p-3 rounded-lg border border-outline-variant">
                      <span className="text-[10px] text-on-surface-variant uppercase font-mono block">Payload URL</span>
                      <span className="text-xs font-mono font-semibold text-primary break-all">
                        {API_BASE ? `${API_BASE}/api/webhooks/github` : 'http://localhost:8000/api/webhooks/github'}
                      </span>
                    </div>

                    <div className="bg-surface-container-lowest p-3 rounded-lg border border-outline-variant">
                      <span className="text-[10px] text-on-surface-variant uppercase font-mono block">Security Verification</span>
                      <span className="text-xs font-mono text-secondary">X-Hub-Signature-256 (HMAC SHA-256)</span>
                    </div>

                    <div className="bg-surface-container-lowest p-3 rounded-lg border border-outline-variant">
                      <span className="text-[10px] text-on-surface-variant uppercase font-mono block">Deduplication</span>
                      <span className="text-xs font-mono text-tertiary">10-Min Signature Window Enabled</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Webhook Simulator */}
              <div className="lg:col-span-7 glass-panel p-6 rounded-2xl border border-primary/30 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-base font-bold text-on-surface flex items-center gap-2">
                      <span className="material-symbols-outlined text-primary">play_circle</span>
                      Simulate Build Failure Webhook
                    </h3>
                    <span className="text-[10px] uppercase font-mono bg-primary/10 text-primary px-2 py-0.5 rounded font-bold">
                      Dev Simulator
                    </span>
                  </div>
                  <p className="text-xs text-on-surface-variant mb-4">
                    Test the complete webhook workflow locally. Generates a signed GitHub <code className="text-primary font-mono">workflow_run.completed</code> payload, checks historical failure memory, and dispatches role-based notifications:
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-semibold text-on-surface-variant">Target Repository</label>
                      <select 
                        value={simRepo}
                        onChange={(e) => setSimRepo(e.target.value)}
                        className="bg-surface-container-lowest border border-outline-variant rounded-lg px-3 py-2 text-xs text-on-surface outline-none"
                      >
                        {repos.map(r => (
                          <option key={r.id} value={r.full_name}>{r.full_name}</option>
                        ))}
                        {repos.length === 0 && (
                          <option value="demo-org/payment-service">demo-org/payment-service (Demo)</option>
                        )}
                      </select>
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-semibold text-on-surface-variant">Workflow Name</label>
                      <input 
                        type="text"
                        value={simWorkflow}
                        onChange={(e) => setSimWorkflow(e.target.value)}
                        className="bg-surface-container-lowest border border-outline-variant rounded-lg px-3 py-2 text-xs text-on-surface outline-none"
                      />
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-semibold text-on-surface-variant">Branch</label>
                      <input 
                        type="text"
                        value={simBranch}
                        onChange={(e) => setSimBranch(e.target.value)}
                        className="bg-surface-container-lowest border border-outline-variant rounded-lg px-3 py-2 text-xs text-on-surface outline-none"
                      />
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-semibold text-on-surface-variant">Commit Message</label>
                      <input 
                        type="text"
                        value={simCommitMsg}
                        onChange={(e) => setSimCommitMsg(e.target.value)}
                        className="bg-surface-container-lowest border border-outline-variant rounded-lg px-3 py-2 text-xs text-on-surface outline-none"
                      />
                    </div>
                  </div>
                </div>

                <div className="mt-6 flex justify-end">
                  <button
                    onClick={handleSimulateWebhook}
                    disabled={isSimulatingWebhook}
                    className="bg-[#5B8CFF] text-white px-6 py-3 rounded-xl font-bold text-sm shadow-[0_4px_20px_rgba(91,140,255,0.4)] hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    {isSimulatingWebhook ? (
                      <>
                        <span className="material-symbols-outlined text-sm animate-spin">refresh</span>
                        Processing Signed Webhook...
                      </>
                    ) : (
                      <>
                        <span className="material-symbols-outlined text-sm">send</span>
                        Simulate & Trigger Failure Webhook
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Pipeline Failure Events Feed */}
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-on-surface flex items-center gap-2">
                  <span className="material-symbols-outlined text-error">history</span>
                  Recent Pipeline Failure Events ({pipelineEvents.length})
                </h3>
                <button 
                  onClick={fetchPipelineEvents}
                  className="text-xs text-primary hover:underline flex items-center gap-1 cursor-pointer"
                >
                  <span className="material-symbols-outlined text-sm">refresh</span>
                  Refresh Events
                </button>
              </div>

              {pipelineEvents.length === 0 ? (
                <div className="glass-panel p-8 text-center rounded-2xl text-on-surface-variant">
                  <span className="material-symbols-outlined text-4xl mb-2 opacity-50">fact_check</span>
                  <p className="font-semibold text-sm">No pipeline failure events recorded yet.</p>
                  <p className="text-xs opacity-70 mt-1">Use the simulator above to generate failure events.</p>
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  {pipelineEvents.map((evt) => (
                    <div key={evt.id} className="glass-panel p-4 rounded-xl border border-outline-variant flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-primary/40 transition-all">
                      <div className="flex items-start gap-3">
                        <div className="w-9 h-9 rounded-lg bg-error/15 text-error flex items-center justify-center shrink-0 mt-0.5">
                          <span className="material-symbols-outlined text-lg">close</span>
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-sm text-on-surface">{evt.repo_full_name}</span>
                            <span className="text-[11px] font-mono text-on-surface-variant">({evt.workflow_name})</span>
                            {evt.analysis?.is_recurring && (
                              <span className="px-2 py-0.5 rounded-full bg-error/15 text-error text-[10px] font-bold">
                                RECURRENT ({evt.analysis.recurrence_count}x)
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-on-surface-variant mt-0.5">
                            Branch: <span className="font-mono font-semibold text-primary">{evt.branch}</span> • Commit: <span className="font-mono">{evt.commit_sha}</span> - {evt.commit_message}
                          </p>
                          {evt.analysis && (
                            <div className="mt-2 text-xs bg-surface-container-highest/60 p-2.5 rounded-lg border border-primary/20">
                              <span className="font-semibold text-primary">AI Diagnosis:</span> {evt.analysis.root_cause}
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="flex md:flex-col items-end justify-between md:justify-center gap-2 shrink-0">
                        <span className="text-[10px] font-mono text-on-surface-variant">
                          {new Date(evt.created_at).toLocaleTimeString()}
                        </span>
                        {evt.analysis ? (
                          <button
                            onClick={() => {
                              if (evt.analysis?.analysis_run_id) {
                                setActiveRunId(evt.analysis.analysis_run_id)
                              }
                              setActiveTab('analysis')
                            }}
                            className="bg-primary/15 text-primary border border-primary/30 px-3 py-1 rounded-lg text-xs font-semibold hover:bg-primary/25 transition-all cursor-pointer"
                          >
                            View Report
                          </button>
                        ) : (
                          <span className="text-[11px] text-tertiary flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></span>
                            Analyzing...
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        )}

        {/* 4. DASHBOARD TAB */}
        {activeTab === 'dashboard' && (
          <section className="max-w-container-max mx-auto px-gutter py-8 flex flex-col gap-6">
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
                
                <div 
                  onClick={() => fileInputRef.current?.click()}
                  className="glass-panel rounded-xl p-6 flex flex-col items-center justify-center text-center border-2 border-dashed border-outline-variant hover:border-primary transition-all group cursor-pointer h-52 relative overflow-hidden"
                >
                  {isUploading ? (
                    <div className="flex flex-col items-center">
                      <span className="material-symbols-outlined text-primary text-5xl animate-spin">sync</span>
                      <h3 className="font-headline-sm text-headline-sm text-on-surface mt-4">Uploading log...</h3>
                    </div>
                  ) : (
                    <div className="relative z-10 flex flex-col items-center">
                      <div className="w-14 h-14 bg-surface-container rounded-full flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                        <span className="material-symbols-outlined text-primary text-3xl">upload_file</span>
                      </div>
                      <h2 className="font-headline-sm text-headline-sm text-on-surface font-semibold mb-1 text-sm">Drop manual debug logs</h2>
                      <p className="text-on-surface-variant text-body-md text-xs">Or click to browse .TXT, .LOG, or .ZIP</p>
                    </div>
                  )}
                </div>

                <div className="glass-panel rounded-xl p-4 flex-grow flex flex-col gap-2.5">
                  <h3 className="font-label-md text-label-md text-on-surface-variant border-b border-outline-variant pb-2">CHOOSE LOG FILE</h3>
                  <div className="flex flex-col gap-2 overflow-y-auto max-h-44 pr-1">
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
                        Run Manual Analysis
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

                      {/* Step 3: Planning & Historical Memory */}
                      {(() => {
                        const step = getStepStatus('planning')
                        return (
                          <div className="flex items-start gap-4 relative z-10">
                            <div className={`absolute left-[-25px] w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${step.status === 'SUCCESS' ? 'bg-tertiary text-on-tertiary' : step.status === 'RUNNING' ? 'bg-primary text-on-primary active-step-glow animate-pulse' : step.status === 'FAILED' ? 'bg-error text-on-error' : 'bg-surface-container-highest text-on-surface-variant'}`}>
                              {step.status === 'SUCCESS' ? <span className="material-symbols-outlined text-sm">check</span> : '3'}
                            </div>
                            <div className="flex-grow grid grid-cols-2">
                              <div>
                                <h3 className={`font-body-lg text-body-lg font-semibold ${step.color}`}>Planning & Investigation</h3>
                                <p className="text-on-surface-variant text-xs mt-0.5">Historical failure correlation, FAISS dense retrieval, and Gemini inference</p>
                              </div>
                              <div className="text-right">
                                <p className="text-on-surface-variant font-mono text-[10px]">{runData?.stages['LLM']?.time ? `${runData.stages['LLM'].time.toFixed(2)}s` : '--'}</p>
                                <p className={`font-semibold text-xs ${step.color}`}>{step.label}</p>
                              </div>
                            </div>
                          </div>
                        )
                      })()}

                      {/* Step 4: Remediation */}
                      {(() => {
                        const step = getStepStatus('remediation')
                        return (
                          <div className="flex items-start gap-4 relative z-10">
                            <div className={`absolute left-[-25px] w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${step.status === 'SUCCESS' ? 'bg-tertiary text-on-tertiary' : step.status === 'RUNNING' ? 'bg-primary text-on-primary active-step-glow animate-pulse' : step.status === 'FAILED' ? 'bg-error text-on-error' : 'bg-surface-container-highest text-on-surface-variant'}`}>
                              {step.status === 'SUCCESS' ? <span className="material-symbols-outlined text-sm">check</span> : '4'}
                            </div>
                            <div className="flex-grow grid grid-cols-2">
                              <div>
                                <h3 className={`font-body-lg text-body-lg font-semibold ${step.color}`}>Remediation & Alerts</h3>
                                <p className="text-on-surface-variant text-xs mt-0.5">Synthesizing fixes and routing role-based notifications</p>
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

                  {runData?.report && (
                    <div className="mt-4 pt-4 border-t border-outline-variant flex justify-end">
                      <button 
                        onClick={() => setActiveTab('analysis')}
                        className="bg-primary text-on-primary px-6 py-2 rounded-lg font-bold text-xs flex items-center gap-2 hover:opacity-90 active:scale-95 transition-all cursor-pointer"
                      >
                        <span>View Diagnosis Report</span>
                        <span className="material-symbols-outlined text-xs">arrow_forward</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>

            </div>

            {/* Bottom Panel: Live Console Logs */}
            <div className="glass-panel rounded-xl flex flex-col h-72 border border-outline-variant terminal-panel overflow-hidden">
              <div className="bg-surface-container-high px-4 py-2.5 border-b border-outline-variant flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-sm">terminal</span>
                  <span className="font-mono text-xs font-semibold text-on-surface">Backend Telemetry & Stage Logs</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-tertiary"></span>
                  <span className="font-mono text-[10px] text-on-surface-variant">STREAM LIVE</span>
                </div>
              </div>

              <div className="flex-grow p-4 font-mono text-xs overflow-y-auto space-y-1.5 leading-relaxed bg-[#0c0e14]">
                {(!runData || runData.console_logs.length === 0) ? (
                  <p className="text-on-surface-variant opacity-50 italic">&gt; Ready. Run an analysis or trigger a webhook simulation to inspect stream.</p>
                ) : (
                  runData.console_logs.map((log, index) => (
                    <div key={index} className="flex items-start gap-2">
                      <span className="text-on-surface-variant opacity-40 shrink-0">[{log.timestamp}]</span>
                      <span className={`font-bold shrink-0 ${log.level === 'ERROR' ? 'text-error' : log.level === 'WARNING' ? 'text-[#ffbd2e]' : 'text-primary'}`}>
                        {log.level}
                      </span>
                      <span className={getLogColor(log.level)}>{log.message}</span>
                    </div>
                  ))
                )}
                <div ref={terminalEndRef} />
              </div>
            </div>

          </section>
        )}

        {/* 5. ANALYSIS TAB (Historical Recurrence & Diagnosis) */}
        {activeTab === 'analysis' && (
          <section className="max-w-container-max mx-auto px-gutter py-8 flex flex-col gap-8">
            {!runData?.report ? (
              <div className="glass-panel p-12 text-center rounded-2xl flex flex-col items-center justify-center min-h-[400px]">
                <span className="material-symbols-outlined text-6xl text-on-surface-variant opacity-40 mb-4">search_off</span>
                <h3 className="text-xl font-bold text-on-surface mb-2">No Active Analysis Report</h3>
                <p className="text-sm text-on-surface-variant max-w-md mb-6">
                  Trigger an automated failure simulation on the Pipeline Monitor tab or run a manual analysis to generate root cause reports.
                </p>
                <div className="flex gap-4">
                  <button 
                    onClick={() => setActiveTab('monitoring')}
                    className="bg-primary text-on-primary px-6 py-2.5 rounded-xl font-bold text-sm"
                  >
                    Go to Pipeline Monitor
                  </button>
                  <button 
                    onClick={() => setActiveTab('dashboard')}
                    className="glass-card px-6 py-2.5 rounded-xl font-semibold text-sm"
                  >
                    Go to Dashboard
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <span className="bg-error/15 text-error px-2.5 py-0.5 rounded text-xs font-mono font-bold">FAILED</span>
                      <h2 className="text-2xl font-bold text-on-surface">{runData.report.failure_type || 'CI/CD Pipeline Failure'}</h2>
                      {runData.report.is_recurring && (
                        <span className="bg-error text-white px-3 py-0.5 rounded-full text-xs font-bold font-mono animate-pulse">
                          RECURRENT FAILURE ({runData.report.recurrence_count}X)
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-on-surface-variant font-mono">Run: {runData.run_id} • Log: {runData.log_name}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <span className="text-[10px] text-on-surface-variant uppercase font-mono block">Critic Confidence</span>
                      <span className="text-lg font-bold font-mono text-tertiary">
                        {((runData.report.final_confidence || 0.95) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <span className="px-3 py-1 bg-tertiary/15 text-tertiary border border-tertiary/25 rounded-full text-xs font-semibold">
                      {runData.report.critic_status || 'VERIFIED'}
                    </span>
                  </div>
                </div>

                {/* Historical Intelligence Banner (Improvement C) */}
                {runData.report.is_recurring && (
                  <div className="p-5 rounded-2xl bg-error/10 border border-error/30 flex flex-col gap-2">
                    <div className="flex items-center gap-2 text-error font-bold text-sm">
                      <span className="material-symbols-outlined text-lg">history</span>
                      <span>Historical Recurrence Detected</span>
                    </div>
                    <p className="text-xs text-on-surface leading-relaxed">
                      {runData.report.intelligence_note}
                    </p>
                  </div>
                )}

                {/* Milestone 5: Granular Classification & Composite Severity Card */}
                {runData.report.failure_category && (
                  <div className="p-4 rounded-2xl bg-surface-container-high border border-outline-variant flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <span className="material-symbols-outlined text-primary text-xl">category</span>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-primary px-2 py-0.5 rounded bg-primary/10">
                            {runData.report.failure_category}
                          </span>
                          <span className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded ${runData.report.severity_tier === 'CRITICAL' ? 'bg-error text-white' : runData.report.severity_tier === 'HIGH' ? 'bg-amber-500/20 text-amber-400' : 'bg-primary/20 text-primary'}`}>
                            {runData.report.severity_tier || 'HIGH'} ({(runData.report.severity_score || 0.70).toFixed(2)})
                          </span>
                        </div>
                        <p className="text-xs text-on-surface-variant mt-1 font-medium">{runData.report.blast_radius}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* AI Root Cause Card */}
                <div className="glass-panel p-6 rounded-2xl border border-primary/30">
                  <h3 className="text-base font-bold text-primary flex items-center gap-2 mb-2">
                    <span className="material-symbols-outlined">psychology</span>
                    AI Root-Cause Diagnosis
                  </h3>
                  <p className="font-semibold text-sm text-on-surface mb-2">{runData.report.root_cause}</p>
                  <p className="text-xs text-on-surface-variant leading-relaxed whitespace-pre-line">{runData.report.explanation}</p>
                </div>

                {/* Suggested Fixes */}
                <div className="glass-panel p-6 rounded-2xl border border-outline-variant">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-base font-bold text-on-surface flex items-center gap-2">
                      <span className="material-symbols-outlined text-tertiary">build</span>
                      Actionable Remediation Steps
                    </h3>
                    <button
                      onClick={executeFix}
                      className="bg-tertiary text-on-tertiary px-4 py-1.5 rounded-lg text-xs font-bold hover:opacity-90 active:scale-95 transition-all cursor-pointer"
                    >
                      Apply Staging Fix
                    </button>
                  </div>

                  <div className="flex flex-col gap-3">
                    {runData.report.suggested_fixes?.map((fix, idx) => (
                      <div key={idx} className="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant flex items-start gap-3">
                        <span className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                          {idx + 1}
                        </span>
                        <p className="text-xs text-on-surface leading-relaxed font-mono">{fix}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Milestone 5: AI-Generated Code-Level Patch & Approval Workflow */}
                {runData.report.code_patch && (
                  <div className="glass-panel p-6 rounded-2xl border border-outline-variant flex flex-col gap-4">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="material-symbols-outlined text-secondary">code_blocks</span>
                          <h3 className="text-base font-bold text-on-surface">{runData.report.code_patch.title}</h3>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                            runData.report.code_patch.status === 'applied' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                            runData.report.code_patch.status === 'approved' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' :
                            runData.report.code_patch.status === 'rejected' ? 'bg-error/20 text-error border border-error/30' :
                            'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          }`}>
                            {runData.report.code_patch.status.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-xs text-on-surface-variant font-mono mt-1">
                          Target: <span className="text-primary font-bold">{runData.report.code_patch.target_file}</span> • Risk: <span className="font-bold">{runData.report.code_patch.risk_level}</span>
                        </p>
                      </div>

                      {/* Human-in-the-Loop Approval Action Controls */}
                      <div className="flex items-center gap-2">
                        {runData.report.code_patch.status === 'pending_review' && (
                          <>
                            <button
                              onClick={() => handleReviewPatch('approve')}
                              className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1 shadow-sm active:scale-95"
                            >
                              <span className="material-symbols-outlined text-sm">thumb_up</span>
                              Approve Patch
                            </button>
                            <button
                              onClick={() => handleReviewPatch('reject')}
                              className="px-3.5 py-1.5 bg-surface-container-highest hover:bg-error/20 text-on-surface-variant hover:text-error rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1 border border-outline-variant active:scale-95"
                            >
                              <span className="material-symbols-outlined text-sm">thumb_down</span>
                              Reject
                            </button>
                          </>
                        )}
                        {runData.report.code_patch.status === 'approved' && (
                          <button
                            onClick={handleApplyPatch}
                            className="px-4 py-1.5 bg-primary hover:bg-primary/90 text-on-primary rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1 shadow-md active:scale-95 animate-pulse"
                          >
                            <span className="material-symbols-outlined text-sm">rocket_launch</span>
                            Apply to Staging
                          </button>
                        )}
                        {runData.report.code_patch.status === 'applied' && (
                          <span className="text-emerald-400 text-xs font-mono font-bold flex items-center gap-1">
                            <span className="material-symbols-outlined text-sm">verified</span>
                            Verified on Staging
                          </span>
                        )}
                      </div>
                    </div>

                    <p className="text-xs text-on-surface-variant leading-relaxed">
                      {runData.report.code_patch.rationale}
                    </p>

                    {/* Syntax-Highlighted Unified Diff Viewer */}
                    <div className="bg-[#12161f] p-4 rounded-xl font-mono text-xs overflow-x-auto border border-outline-variant/60 shadow-inner max-h-64">
                      {runData.report.code_patch.diff_content.split('\n').map((line, lIdx) => {
                        const isAdd = line.startsWith('+') && !line.startsWith('+++')
                        const isDel = line.startsWith('-') && !line.startsWith('---')
                        const isHunk = line.startsWith('@@')
                        const isHeader = line.startsWith('diff --git') || line.startsWith('---') || line.startsWith('+++')
                        return (
                          <div
                            key={lIdx}
                            className={`${
                              isAdd ? 'text-emerald-400 bg-emerald-950/30' :
                              isDel ? 'text-rose-400 bg-rose-950/30' :
                              isHunk ? 'text-cyan-400 bg-cyan-950/20' :
                              isHeader ? 'text-on-surface-variant font-bold' :
                              'text-on-surface-variant'
                            } px-2 py-0.5 rounded leading-relaxed`}
                          >
                            {line || ' '}
                          </div>
                        )
                      })}
                    </div>

                    {runData.report.code_patch.validation_command && (
                      <div className="text-[11px] font-mono text-on-surface-variant flex items-center gap-2">
                        <span className="text-primary font-bold">Verification:</span>
                        <code className="bg-surface-container-highest px-2 py-0.5 rounded text-secondary">
                          {runData.report.code_patch.validation_command}
                        </code>
                      </div>
                    )}
                  </div>
                )}

                {/* Past Occurrences Table */}
                {runData.report.past_occurrences && runData.report.past_occurrences.length > 0 && (
                  <div className="glass-panel p-6 rounded-2xl border border-outline-variant">
                    <h3 className="text-base font-bold text-on-surface mb-3 flex items-center gap-2">
                      <span className="material-symbols-outlined text-primary">manage_search</span>
                      Previous Occurrences in Repository
                    </h3>
                    <div className="flex flex-col gap-2">
                      {runData.report.past_occurrences.map((past, i) => (
                        <div key={i} className="p-3 bg-surface-container-lowest rounded-xl border border-outline-variant/60 flex items-center justify-between text-xs">
                          <div>
                            <span className="font-mono text-primary font-bold">Branch: {past.branch}</span> • <span className="font-mono">Commit: {past.commit_sha}</span>
                            <p className="text-[11px] text-on-surface-variant mt-0.5">{past.root_cause}</p>
                          </div>
                          <span className="text-[10px] font-mono text-on-surface-variant">
                            {past.timestamp ? new Date(past.timestamp).toLocaleDateString() : 'Historical'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </section>
        )}

        {/* 6. ARCHITECTURE TAB */}
        {activeTab === 'architecture' && (
          <section className="max-w-container-max mx-auto px-gutter py-8 flex flex-col gap-8">
            <div>
              <h2 className="text-2xl font-bold text-on-surface">Pipeline Failure Detection 3.0 Architecture</h2>
              <p className="text-sm text-on-surface-variant">Enterprise infrastructure uniting GitHub Webhooks, HMAC verification, two-tier RBAC, Role-Based Routing, and Historical Memory.</p>
            </div>

            <div className="glass-panel p-8 rounded-2xl border border-outline-variant">
              <h3 className="text-base font-bold text-primary mb-4">Pipeline Failure Detection 3.0 Lifecycle</h3>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant">
                  <span className="text-[10px] font-mono text-primary font-bold block mb-1">STEP 1</span>
                  <h4 className="font-bold text-sm mb-1">Webhook Ingestion</h4>
                  <p className="text-xs text-on-surface-variant">Receives `workflow_run.completed` with failure. Validates HMAC SHA-256 signature.</p>
                </div>
                <div className="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant">
                  <span className="text-[10px] font-mono text-primary font-bold block mb-1">STEP 2</span>
                  <h4 className="font-bold text-sm mb-1">Historical Memory</h4>
                  <p className="text-xs text-on-surface-variant">Correlates error signature against past failures. Flags recurrence count and past fixes.</p>
                </div>
                <div className="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant">
                  <span className="text-[10px] font-mono text-primary font-bold block mb-1">STEP 3</span>
                  <h4 className="font-bold text-sm mb-1">Agentic RAG</h4>
                  <p className="text-xs text-on-surface-variant">Dense FAISS similarity search, Gemini prompt with historical context, Critic validation.</p>
                </div>
                <div className="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant">
                  <span className="text-[10px] font-mono text-primary font-bold block mb-1">STEP 4</span>
                  <h4 className="font-bold text-sm mb-1">Role-Based Routing</h4>
                  <p className="text-xs text-on-surface-variant">Throttles duplicates. Dispatches alerts to Owners, Admins, or Devs via In-App, Slack, Discord.</p>
                </div>
              </div>
            </div>
          </section>
        )}

      </main>

      {/* Footer bar */}
      <footer className="bg-surface-container-lowest border-t border-outline-variant w-full py-4 text-xs mt-auto">
        <div className="flex flex-col md:flex-row justify-between items-center px-gutter w-full max-w-container-max mx-auto gap-2">
          <div className="flex flex-col gap-0.5">
            <span className="font-semibold text-on-surface-variant uppercase tracking-wider text-[10px]">Pipeline Failure Detection 3.0</span>
            <p className="text-secondary">© 2026 DevOps Reliability Platform. Milestone 1, 2 & 3 Active.</p>
          </div>
          <div className="flex gap-4">
            <a className="text-on-surface-variant hover:text-tertiary transition-colors" href="#">Milestone 1: RBAC</a>
            <a className="text-on-surface-variant hover:text-tertiary transition-colors" href="#">Milestone 2: Webhooks</a>
            <a className="text-on-surface-variant hover:text-tertiary transition-colors" href="#">Milestone 3: Notification Engine</a>
            <a className="text-on-surface-variant hover:text-tertiary transition-colors" href="#">Milestone 5: Historical RAG</a>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
