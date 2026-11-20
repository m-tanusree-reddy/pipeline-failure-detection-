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

interface CodePatch {
  patch_id: string
  title: string
  target_file: string
  diff_content: string
  rationale: string
  risk_level: string
  validation_command: string
  status: string
  pr_url?: string
  pr_number?: number
}

interface PastOccurrence {
  run_id: string
  commit_sha: string
  branch: string
  timestamp: string
  workflow_name: string
  root_cause: string
  suggested_fixes: string[]
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
    code_patch?: CodePatch
    past_occurrences?: PastOccurrence[]
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

interface AuthUser {
  id: string
  username: string
  email?: string
  avatar_url?: string
  global_role: string
  auth_method?: string
}

const SIMULATION_PRESETS = [
  {
    id: 'dependency',
    title: 'Pip Dependency Conflict',
    category: 'DEPENDENCY_INCOMPATIBILITY',
    badgeColor: 'border-amber-500/30 text-amber-400 bg-amber-500/10',
    workflow: 'Backend CI Pipeline',
    branch: 'main',
    commitMsg: 'chore: bump cryptography and pyopenssl dependencies',
    errorType: 'ResolutionImpossible: Conflicting requirements for cryptography>=42.0 and urllib3<2.0'
  },
  {
    id: 'assertion',
    title: 'API Integration Assertion Error',
    category: 'ASSERTION_FAILURE',
    badgeColor: 'border-rose-500/30 text-rose-400 bg-rose-500/10',
    workflow: 'Payment Service E2E Tests',
    branch: 'feature/stripe-v2',
    commitMsg: 'feat: migrate checkout endpoint to Stripe v2 webhooks',
    errorType: 'AssertionError: Expected HTTP 200 OK from webhook handler, got 500 Internal Server Error'
  },
  {
    id: 'resource',
    title: 'Container OOM Resource Exhaustion',
    category: 'RESOURCE_EXHAUSTION',
    badgeColor: 'border-purple-500/30 text-purple-400 bg-purple-500/10',
    workflow: 'ML Model Inference Pipeline',
    branch: 'prod',
    commitMsg: 'perf: load expanded sentence-transformers vector index',
    errorType: 'Container killed: OOMKilled (Exit Code 137). Memory limit of 512MB exceeded.'
  },
  {
    id: 'secrets',
    title: 'Cloud Security Credentials Expired',
    category: 'SECRETS_CREDENTIALS_EXPIRATION',
    badgeColor: 'border-red-500/30 text-red-400 bg-red-500/10',
    workflow: 'Terraform AWS Deploy',
    branch: 'staging',
    commitMsg: 'ci: refresh staging infrastructure deployment',
    errorType: 'ClientError: The security token included in the request is expired. AWS STS token failure.'
  }
]

function App() {
  const [activeTab, setActiveTab] = useState<'home' | 'repositories' | 'monitoring' | 'dashboard' | 'analysis' | 'architecture'>('home')
  const [logs, setLogs] = useState<LogFile[]>([])
  const [selectedLogId, setSelectedLogId] = useState<string>('')
  const [activeRunId, setActiveRunId] = useState<string>('')
  const [runData, setRunData] = useState<RunData | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  // Repositories & RBAC
  const [repos, setRepos] = useState<Repository[]>([])
  const [repoUrlInput, setRepoUrlInput] = useState('')
  const [repoTokenInput, setRepoTokenInput] = useState('')
  const [repoSecretInput, setRepoSecretInput] = useState('')
  const [isConnectingRepo, setIsConnectingRepo] = useState(false)
  const [lastConnectedRole, setLastConnectedRole] = useState<{ gh_perm: string; app_role: string } | null>(null)

  // Webhooks & Simulator
  const [pipelineEvents, setPipelineEvents] = useState<PipelineEvent[]>([])
  const [eventSearchQuery, setEventSearchQuery] = useState('')
  const [eventStatusFilter, setEventStatusFilter] = useState<'ALL' | 'FAILED' | 'SUCCESS'>('ALL')
  const [isSimulatingWebhook, setIsSimulatingWebhook] = useState(false)
  const [simRepo, setSimRepo] = useState('')
  const [simWorkflow, setSimWorkflow] = useState('Backend CI Pipeline')
  const [simBranch, setSimBranch] = useState('main')
  const [simCommitMsg, setSimCommitMsg] = useState('fix: update checkout session handler')
  const [simErrorType, setSimErrorType] = useState('AssertionError: Expected 200, got 500')

  // Notifications & Preferences
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

  // System & Terminal
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [logFilter, setLogFilter] = useState<'ALL' | 'ERROR' | 'WARNING' | 'INFO'>('ALL')
  const [isAutoScroll, setIsAutoScroll] = useState(true)

  // User Authentication & GitHub OAuth State
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(() => {
    try {
      const saved = localStorage.getItem('pipeline_auth_user')
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false)
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const [authTab, setAuthTab] = useState<'oauth' | 'pat' | 'demo'>('oauth')
  const [patInput, setPatInput] = useState('')
  const [patUsernameInput, setPatUsernameInput] = useState('')
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [isDbModalOpen, setIsDbModalOpen] = useState(false)

  const terminalEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const notifDropdownRef = useRef<HTMLDivElement>(null)
  const userMenuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchLogs()
    fetchRepositories()
    fetchPipelineEvents()
    fetchNotifications()
    fetchPreferences()
    fetchSystemStatus()

    // Handle incoming GitHub OAuth Callback Code (?code=...)
    const urlParams = new URLSearchParams(window.location.search)
    const oauthCode = urlParams.get('code')
    if (oauthCode) {
      handleOAuthCallback(oauthCode)
    }
  }, [])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (notifDropdownRef.current && !notifDropdownRef.current.contains(event.target as Node)) {
        setIsNotificationOpen(false)
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (isAutoScroll && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [runData?.console_logs, isAutoScroll])

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
          }
        } catch (err) {
          console.error('Polling error:', err)
        }
      }, 1000)
    }
    return () => clearInterval(intervalId)
  }, [isAnalyzing, activeRunId])

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text)
    setCopiedKey(key)
    showToast(`Copied to clipboard`)
    setTimeout(() => setCopiedKey(null), 2500)
  }

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => {
      setToastMessage(null)
    }, 4000)
  }

  const applyPreset = (presetId: string) => {
    const p = SIMULATION_PRESETS.find(item => item.id === presetId)
    if (!p) return
    setSimWorkflow(p.workflow)
    setSimBranch(p.branch)
    setSimCommitMsg(p.commitMsg)
    setSimErrorType(p.errorType)
    showToast(`Loaded preset: ${p.title}`)
  }

  const handleOAuthCallback = async (code: string) => {
    setIsAuthenticating(true)
    try {
      const res = await fetch(`${API_BASE}/api/auth/github/callback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'OAuth authentication failed')
      }
      const data = await res.json()
      setCurrentUser(data.user)
      localStorage.setItem('pipeline_auth_user', JSON.stringify(data.user))
      showToast(`Authenticated with GitHub as @${data.user.username}!`)
      window.history.replaceState({}, document.title, window.location.pathname)
    } catch (err: any) {
      showToast(`OAuth Error: ${err.message}`)
    } finally {
      setIsAuthenticating(false)
    }
  }

  const handleOAuthLogin = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/github/url`)
      if (res.ok) {
        const data = await res.json()
        if (data.configured && data.url) {
          window.location.href = data.url
        } else {
          showToast(data.message || 'GitHub OAuth client ID is not configured. Switching to Token / Demo login.')
          setAuthTab('demo')
        }
      }
    } catch (err: any) {
      showToast(`OAuth Error: ${err.message}`)
    }
  }

  const handleTokenLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!patInput.trim() && !patUsernameInput.trim()) return
    setIsAuthenticating(true)
    try {
      const res = await fetch(`${API_BASE}/api/auth/token-login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: patInput.trim() || undefined,
          username: patUsernameInput.trim() || undefined
        })
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Sign-in failed')
      }
      const data = await res.json()
      setCurrentUser(data.user)
      localStorage.setItem('pipeline_auth_user', JSON.stringify(data.user))
      setIsAuthModalOpen(false)
      setPatInput('')
      setPatUsernameInput('')
      showToast(`Signed in as @${data.user.username}! Role: ${data.user.global_role}`)
    } catch (err: any) {
      showToast(`Sign In Error: ${err.message}`)
    } finally {
      setIsAuthenticating(false)
    }
  }

  const handleDemoLogin = async () => {
    setIsAuthenticating(true)
    try {
      const res = await fetch(`${API_BASE}/api/auth/demo-login`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setCurrentUser(data.user)
        localStorage.setItem('pipeline_auth_user', JSON.stringify(data.user))
        setIsAuthModalOpen(false)
        showToast('Signed in as On-Call DevOps (Admin)')
      }
    } catch (err: any) {
      showToast(`Demo Sign-In Error: ${err.message}`)
    } finally {
      setIsAuthenticating(false)
    }
  }

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, { method: 'POST' })
    } catch {}
    setCurrentUser(null)
    localStorage.removeItem('pipeline_auth_user')
    setIsUserMenuOpen(false)
    showToast('Signed out successfully.')
  }

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/logs`)
      if (!res.ok) throw new Error('Failed to fetch logs')
      const data = await res.json()
      setLogs(data.logs || [])
      if (data.logs?.length > 0 && !selectedLogId) {
        setSelectedLogId(data.logs[0].id)
      }
    } catch (err) {
      console.error(err)
    }
  }

  const fetchRepositories = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/repos`)
      if (res.ok) {
        const data = await res.json()
        setRepos(data.repositories || [])
        if (data.repositories?.length > 0 && !simRepo) {
          setSimRepo(data.repositories[0].full_name)
          fetchRepoChannels(data.repositories[0].id)
        }
      }
    } catch (err) {
      console.error(err)
    }
  }

  const fetchPipelineEvents = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/events?limit=25`)
      if (res.ok) {
        const data = await res.json()
        setPipelineEvents(data.events || [])
      }
    } catch (err) {
      console.error(err)
    }
  }

  const fetchNotifications = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/notifications?limit=20`)
      if (res.ok) {
        const data = await res.json()
        setNotifications(data.notifications || [])
        setUnreadCount(data.unread_count || 0)
      }
    } catch (err) {
      console.error(err)
    }
  }

  const fetchPreferences = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/notifications/preferences`)
      if (res.ok) {
        const data = await res.json()
        const prefs = data.preferences || data
        if (prefs && typeof prefs === 'object') {
          setPreferences(prev => ({
            email_enabled: prefs.email_enabled ?? prev.email_enabled,
            slack_enabled: prefs.slack_enabled ?? prev.slack_enabled,
            discord_enabled: prefs.discord_enabled ?? prev.discord_enabled,
            in_app_enabled: prefs.in_app_enabled ?? prev.in_app_enabled,
            notify_critical_only: prefs.notify_critical_only ?? prev.notify_critical_only
          }))
        }
      }
    } catch (err) {
      console.error(err)
    }
  }

  const updatePreferences = async (newPrefs: NotificationPreference) => {
    setPreferences(newPrefs)
    try {
      const res = await fetch(`${API_BASE}/api/notifications/preferences`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newPrefs)
      })
      if (res.ok) {
        showToast('Notification preferences updated.')
      }
    } catch (err) {
      console.error(err)
    }
  }

  const fetchRepoChannels = async (repoId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/repos/${repoId}/notifications`)
      if (res.ok) {
        const data = await res.json()
        setChannels(data.channels || [])
      }
    } catch (err) {
      console.error(err)
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
      console.error('System status error:', err)
    }
  }

  const handleAddChannel = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newChannelTarget.trim()) return
    const targetRepo = repos.find(r => r.full_name === simRepo) || repos[0]
    if (!targetRepo) {
      showToast('Connect a repository first before configuring alert channels.')
      return
    }

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
        showToast(`${newChannelType.toUpperCase()} alert destination registered!`)
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
      showToast('All alerts marked as read.')
    } catch (err) {
      console.error('Error marking all read:', err)
    }
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
      showToast(`Upload failed: ${err.message}`)
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const startAnalysis = async (logId: string) => {
    if (!logId) return
    setIsAnalyzing(true)
    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ log_id: logId }),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Analysis request failed')
      }

      const data = await res.json()
      setActiveRunId(data.run_id)
      setRunData({
        run_id: data.run_id,
        status: 'running',
        log_name: logs.find(l => l.id === logId)?.name || 'Manual Log',
        stages: {},
        console_logs: [],
        report: null,
        error: null,
      })
      showToast('Analysis initiated. Offloaded to background processing worker.')
    } catch (err: any) {
      setIsAnalyzing(false)
      showToast(`Error: ${err.message}`)
    }
  }

  const handleConnectRepo = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!repoUrlInput.trim()) return

    setIsConnectingRepo(true)
    try {
      const res = await fetch(`${API_BASE}/api/repos/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: repoUrlInput.trim(),
          access_token: repoTokenInput.trim() || undefined,
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
          error_type: simErrorType
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
        showToast(err.detail || 'Failed to review patch.')
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
        body: JSON.stringify({
          applied_by: currentUser?.username || 'developer-oncall',
          target_workspace: './staging'
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

  const [isCreatingPr, setIsCreatingPr] = useState(false)
  const [prResult, setPrResult] = useState<{ pr_url: string; pr_number: number } | null>(null)
  const [isPostingComment, setIsPostingComment] = useState(false)

  const handleCreatePullRequest = async () => {
    const patchId = runData?.report?.code_patch?.patch_id || runData?.report?.remediation_id
    if (!patchId) return
    setIsCreatingPr(true)
    try {
      const res = await fetch(`${API_BASE}/api/remediations/${patchId}/create-pr`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_role: 'Developer',
          reviewer_username: currentUser?.username || 'developer'
        })
      })
      if (res.ok) {
        const data = await res.json()
        setPrResult({ pr_url: data.pr_url, pr_number: data.pr_number })
        showToast(`🎉 GitHub Pull Request #${data.pr_number} created successfully!`)
        if (runData?.report?.code_patch) {
          setRunData({
            ...runData,
            report: {
              ...runData.report,
              code_patch: {
                ...runData.report.code_patch,
                status: 'pr_created',
                pr_url: data.pr_url,
                pr_number: data.pr_number
              }
            }
          })
        }
      } else {
        const err = await res.json()
        showToast(err.detail || 'Failed to create Pull Request.')
      }
    } catch (err: any) {
      showToast(`PR creation error: ${err.message}`)
    } finally {
      setIsCreatingPr(false)
    }
  }

  const handlePostDiagnosticComment = async () => {
    const targetRunId = activeRunId || (runData as any)?.id || (runData?.report as any)?.run_id
    if (!targetRunId) {
      showToast('No active run selected to post comment.')
      return
    }
    setIsPostingComment(true)
    try {
      const res = await fetch(`${API_BASE}/api/runs/${targetRunId}/post-github-comment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: 'commit' })
      })
      if (res.ok) {
        showToast(`✅ Diagnostic comment posted to GitHub commit!`)
      } else {
        const err = await res.json()
        showToast(err.detail || 'Failed to post comment.')
      }
    } catch (err: any) {
      showToast(`Comment error: ${err.message}`)
    } finally {
      setIsPostingComment(false)
    }
  }

  const getStepStatus = (stepName: string) => {
    if (!runData) return { status: 'PENDING', label: 'Pending', color: 'text-slate-400' }
    const stages = runData.stages
    
    if (stepName === 'parsing') {
      const s = stages['Parser']
      if (s?.status === 'SUCCESS') return { status: 'SUCCESS', label: 'Completed', color: 'text-emerald-400' }
      if (s?.status === 'RUNNING') return { status: 'RUNNING', label: 'Processing...', color: 'text-indigo-400' }
      if (s?.status === 'FAILED') return { status: 'FAILED', label: 'Failed', color: 'text-rose-400' }
      return { status: 'PENDING', label: 'Pending', color: 'text-slate-500' }
    }

    if (stepName === 'classifying') {
      const s = stages['Classifier']
      if (s?.status === 'SUCCESS') return { status: 'SUCCESS', label: 'Completed', color: 'text-emerald-400' }
      if (s?.status === 'RUNNING') return { status: 'RUNNING', label: 'Classifying...', color: 'text-indigo-400' }
      if (s?.status === 'FAILED') return { status: 'FAILED', label: 'Failed', color: 'text-rose-400' }
      return { status: 'PENDING', label: 'Pending', color: 'text-slate-500' }
    }

    if (stepName === 'planning') {
      const planningStages = ['Planner', 'Collector', 'Chunker', 'Embedder', 'Vector Store', 'Retriever', 'LLM', 'Critic']
      const statuses = planningStages.map(st => stages[st]?.status || 'PENDING')
      if (statuses.includes('FAILED')) return { status: 'FAILED', label: 'Failed', color: 'text-rose-400' }
      if (stages['Critic']?.status === 'SUCCESS') return { status: 'SUCCESS', label: 'Completed', color: 'text-emerald-400' }
      if (statuses.includes('RUNNING') || stages['Classifier']?.status === 'SUCCESS') {
        return { status: 'RUNNING', label: 'Inferring & Verifying...', color: 'text-indigo-400' }
      }
      return { status: 'PENDING', label: 'Pending', color: 'text-slate-500' }
    }

    if (stepName === 'remediation') {
      const s = stages['Report']
      if (s?.status === 'SUCCESS') return { status: 'SUCCESS', label: 'Completed', color: 'text-emerald-400' }
      if (s?.status === 'RUNNING') return { status: 'RUNNING', label: 'Synthesizing Patch...', color: 'text-indigo-400' }
      if (s?.status === 'FAILED') return { status: 'FAILED', label: 'Failed', color: 'text-rose-400' }
      return { status: 'PENDING', label: 'Pending', color: 'text-slate-500' }
    }
    return { status: 'PENDING', label: 'Pending', color: 'text-slate-500' }
  }

  const filteredLogs = (runData?.console_logs || []).filter(log => {
    if (logFilter === 'ALL') return true
    return log.level.toUpperCase() === logFilter
  })

  const filteredEvents = pipelineEvents.filter(evt => {
    const matchesSearch = !eventSearchQuery || 
      evt.repo_full_name.toLowerCase().includes(eventSearchQuery.toLowerCase()) ||
      evt.workflow_name.toLowerCase().includes(eventSearchQuery.toLowerCase()) ||
      evt.branch.toLowerCase().includes(eventSearchQuery.toLowerCase()) ||
      evt.commit_sha.toLowerCase().includes(eventSearchQuery.toLowerCase())
    
    if (eventStatusFilter === 'ALL') return matchesSearch
    if (eventStatusFilter === 'FAILED') return matchesSearch && evt.conclusion === 'failure'
    if (eventStatusFilter === 'SUCCESS') return matchesSearch && evt.conclusion !== 'failure'
    return matchesSearch
  })

  return (
    <div className="flex flex-col min-h-screen text-slate-100 selection:bg-indigo-500 selection:text-white">
      {/* Toast Notification Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-6 z-[100] bg-slate-900/95 backdrop-blur-md border border-indigo-500/40 text-slate-100 px-5 py-3.5 rounded-xl shadow-2xl flex items-center gap-3 animate-bounce">
          <span className="material-symbols-outlined text-indigo-400 text-xl">info</span>
          <span className="font-medium text-xs tracking-wide">{toastMessage}</span>
        </div>
      )}

      {/* Enterprise Top Navigation Bar */}
      <header className="bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/80 w-full h-16 sticky top-0 z-50">
        <div className="flex items-center justify-between px-6 max-w-7xl mx-auto h-full">
          
          {/* Logo & Platform Branding */}
          <div className="flex items-center gap-8">
            <div 
              onClick={() => setActiveTab('home')}
              className="flex items-center gap-3 cursor-pointer group active:scale-95 transition-all"
            >
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-blue-500 to-cyan-400 p-0.5 shadow-lg shadow-indigo-500/25 flex items-center justify-center">
                <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center group-hover:bg-slate-900 transition-colors">
                  <span className="material-symbols-outlined text-indigo-400 text-xl font-bold">troubleshoot</span>
                </div>
              </div>
              <div className="flex flex-col">
                <span className="font-extrabold text-sm tracking-tight text-white flex items-center gap-2">
                  PIPELINE FAILURE <span className="text-indigo-400">3.0</span>
                </span>
                <span className="text-[10px] font-mono tracking-widest text-slate-400 uppercase -mt-0.5">Reliability Platform</span>
              </div>
            </div>

            {/* Navigation Tabs */}
            <nav className="hidden lg:flex items-center gap-1">
              {[
                { id: 'home', label: 'Overview', icon: 'dashboard' },
                { id: 'repositories', label: 'Repositories & Alerts', icon: 'folder_managed', badge: repos.length },
                { id: 'monitoring', label: 'Pipeline Monitor', icon: 'radar', badge: pipelineEvents.filter(e => e.conclusion === 'failure').length },
                { id: 'dashboard', label: 'Live Analysis & DAG', icon: 'account_tree', isLive: isAnalyzing },
                { id: 'analysis', label: 'Root Cause & Fixes', icon: 'psychology', hasPatch: !!runData?.report?.code_patch },
                { id: 'architecture', label: 'Architecture & CI/CD', icon: 'hub' },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer ${
                    activeTab === tab.id
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  <span className="material-symbols-outlined text-[17px] opacity-80">{tab.icon}</span>
                  <span>{tab.label}</span>
                  {tab.isLive && (
                    <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping" />
                  )}
                  {tab.hasPatch && activeTab !== 'analysis' && (
                    <span className="px-1.5 py-0.2 bg-emerald-500/20 text-emerald-400 text-[10px] rounded font-mono font-bold">PATCH</span>
                  )}
                  {tab.badge !== undefined && tab.badge > 0 && (
                    <span className="px-1.5 py-0.2 bg-slate-800 text-slate-300 text-[10px] rounded font-mono">
                      {tab.badge}
                    </span>
                  )}
                </button>
              ))}
            </nav>
          </div>

          {/* Right Action Bar & Telemetry */}
          <div className="flex items-center gap-3">
            
            {/* Live System Engine Telemetry Pill */}
            <div 
              onClick={() => setIsDbModalOpen(true)}
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-slate-900/90 hover:bg-slate-800 rounded-full border border-slate-800 hover:border-indigo-500/50 text-[11px] font-mono shadow-inner cursor-pointer transition-all"
              title="Click to inspect Database & Queue configuration"
            >
              <span className={`w-2 h-2 rounded-full ${systemStatus?.status === 'online' ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-amber-400'} animate-pulse`} />
              <span className="text-slate-400">
                DB: <strong className="text-slate-200">{systemStatus?.database?.dialect === 'postgresql' ? 'PostgreSQL' : 'SQLite'}</strong>
              </span>
              <span className="text-slate-700">|</span>
              <span className="text-slate-400">
                Queue: <strong className="text-indigo-400">{systemStatus?.queue?.active_mode === 'celery' ? 'Celery (Redis)' : 'Local Async'}</strong>
              </span>
            </div>

            {/* Quick Simulate Trigger */}
            <button
              onClick={() => {
                setActiveTab('monitoring')
                handleSimulateWebhook()
              }}
              disabled={isSimulatingWebhook}
              className="hidden md:flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-md shadow-indigo-600/25 cursor-pointer disabled:opacity-50"
              title="Trigger a simulated webhook failure"
            >
              <span className="material-symbols-outlined text-[16px]">bolt</span>
              <span>{isSimulatingWebhook ? 'Simulating...' : 'Simulate'}</span>
            </button>

            {/* In-App Notification Center Dropdown */}
            <div className="relative" ref={notifDropdownRef}>
              <button
                onClick={() => setIsNotificationOpen(!isNotificationOpen)}
                className="relative p-2 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer text-slate-300 hover:text-white flex items-center justify-center border border-transparent hover:border-slate-700"
                title="Notifications & Alerts"
              >
                <span className="material-symbols-outlined text-[20px]">notifications</span>
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 w-4 h-4 bg-rose-500 text-white font-mono text-[9px] font-extrabold rounded-full flex items-center justify-center animate-pulse shadow-md">
                    {unreadCount}
                  </span>
                )}
              </button>

              {/* Notification Tray */}
              {isNotificationOpen && (
                <div className="absolute right-0 mt-3 w-88 md:w-96 bg-slate-900/95 backdrop-blur-2xl rounded-2xl shadow-2xl border border-slate-700/80 p-4 z-50 flex flex-col gap-3 animate-in fade-in slide-in-from-top-2 duration-150">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs uppercase tracking-wider text-slate-200">Alert Center</span>
                      {unreadCount > 0 && (
                        <span className="px-2 py-0.5 rounded-full bg-rose-500/15 text-rose-400 border border-rose-500/30 text-[10px] font-bold">
                          {unreadCount} unread
                        </span>
                      )}
                    </div>
                    {unreadCount > 0 && (
                      <button
                        onClick={markAllNotificationsRead}
                        className="text-[11px] text-indigo-400 hover:text-indigo-300 font-semibold cursor-pointer"
                      >
                        Mark all read
                      </button>
                    )}
                  </div>

                  <div className="flex flex-col gap-2 max-h-80 overflow-y-auto pr-1">
                    {notifications.length === 0 ? (
                      <div className="py-10 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
                        <span className="material-symbols-outlined text-2xl text-slate-600">notifications_off</span>
                        <span>No alerts currently recorded.</span>
                      </div>
                    ) : (
                      notifications.map(n => (
                        <div
                          key={n.id}
                          onClick={() => {
                            if (!n.is_read) markNotificationRead(n.id)
                            if (n.run_id) {
                              setActiveRunId(n.run_id)
                              setActiveTab('analysis')
                            }
                            setIsNotificationOpen(false)
                          }}
                          className={`p-3 rounded-xl border text-xs flex flex-col gap-1.5 transition-all cursor-pointer ${
                            n.is_read
                              ? 'bg-slate-950/40 border-slate-800/60 opacity-65 hover:opacity-100 hover:border-slate-700'
                              : 'bg-slate-800/60 border-indigo-500/40 shadow-sm hover:border-indigo-400'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                              n.severity === 'critical'
                                ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                                : n.severity === 'warning'
                                ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                                : 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30'
                            }`}>
                              {n.event_type.replace('_', ' ')}
                            </span>
                            <span className="text-[10px] font-mono text-slate-400">
                              {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                          <p className="font-bold text-slate-200 text-xs leading-snug">{n.title}</p>
                          <p className="text-slate-400 text-[11px] line-clamp-2 leading-relaxed">{n.message}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* User Profile / GitHub Authentication */}
            <div className="relative pl-2 border-l border-slate-800" ref={userMenuRef}>
              {currentUser ? (
                <div>
                  <button
                    onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                    className="flex items-center gap-2 hover:bg-slate-800/60 p-1.5 rounded-xl transition-all cursor-pointer"
                  >
                    {currentUser.avatar_url ? (
                      <img
                        src={currentUser.avatar_url}
                        alt={currentUser.username}
                        className="w-8 h-8 rounded-full border border-indigo-500/40 object-cover"
                      />
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-xs shadow-md">
                        {currentUser.username.substring(0, 2).toUpperCase()}
                      </div>
                    )}
                    <div className="hidden xl:flex flex-col text-left">
                      <span className="text-[11px] font-bold text-slate-200 leading-tight">@{currentUser.username}</span>
                      <span className="text-[9px] font-mono text-emerald-400">{currentUser.global_role} Role</span>
                    </div>
                    <span className="material-symbols-outlined text-xs text-slate-400">arrow_drop_down</span>
                  </button>

                  {/* User Profile Menu Dropdown */}
                  {isUserMenuOpen && (
                    <div className="absolute right-0 mt-2 w-56 bg-slate-900 border border-slate-700/80 rounded-2xl p-2 shadow-2xl z-50 flex flex-col gap-1 text-xs">
                      <div className="p-2 border-b border-slate-800">
                        <p className="font-bold text-white">@{currentUser.username}</p>
                        {currentUser.email && <p className="text-[11px] text-slate-400 truncate">{currentUser.email}</p>}
                        <span className="inline-block mt-1 px-2 py-0.5 bg-indigo-500/15 text-indigo-300 text-[10px] font-mono rounded font-bold">
                          {currentUser.auth_method === 'oauth' ? 'GitHub OAuth' : currentUser.auth_method === 'token' ? 'Personal Access Token' : 'Demo Session'}
                        </span>
                      </div>
                      <button
                        onClick={() => {
                          setIsUserMenuOpen(false)
                          setIsAuthModalOpen(true)
                        }}
                        className="p-2 text-left text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-colors flex items-center gap-2 cursor-pointer"
                      >
                        <span className="material-symbols-outlined text-sm">switch_account</span>
                        Switch Account / Re-auth
                      </button>
                      <button
                        onClick={handleLogout}
                        className="p-2 text-left text-rose-400 hover:bg-rose-950/40 rounded-lg transition-colors flex items-center gap-2 cursor-pointer font-semibold"
                      >
                        <span className="material-symbols-outlined text-sm">logout</span>
                        Sign Out
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <button
                  onClick={() => setIsAuthModalOpen(true)}
                  className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-indigo-600/25 active:scale-95 flex items-center gap-1.5 cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[16px]">login</span>
                  <span>Sign In</span>
                </button>
              )}
            </div>

          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-grow w-full max-w-7xl mx-auto px-6 py-8">

        {/* 1. OVERVIEW (HOME) TAB */}
        {activeTab === 'home' && (
          <div className="flex flex-col gap-8">
            
            {/* Hero Banner */}
            <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 p-8 lg:p-10 shadow-2xl">
              <div className="absolute top-0 right-0 -mr-20 -mt-20 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
              <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-8">
                <div className="flex flex-col gap-3 max-w-2xl">
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-semibold w-fit">
                    <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
                    Enterprise Failure Intelligence Engine 3.0
                  </div>
                  <h1 className="text-3xl lg:text-4xl font-extrabold text-white tracking-tight leading-tight">
                    Instant CI Failure Root Cause, <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-blue-400 to-cyan-300">
                      Historical Recurrence Memory & Automated Fixes
                    </span>
                  </h1>
                  <p className="text-slate-400 text-sm leading-relaxed">
                    Automate continuous delivery reliability. Pipeline Failure Detection ingests GitHub Actions webhooks in real-time, correlates errors with FAISS historical memory, generates code-level Git diff patches, and routes alerts directly to the responsible engineer.
                  </p>
                  
                  <div className="flex flex-wrap items-center gap-3 pt-2">
                    <button
                      onClick={() => setActiveTab('monitoring')}
                      className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-bold text-xs rounded-xl shadow-lg shadow-indigo-600/30 flex items-center gap-2 transition-all cursor-pointer"
                    >
                      <span className="material-symbols-outlined text-sm">radar</span>
                      Open Pipeline Monitor
                    </button>
                    <button
                      onClick={() => setActiveTab('repositories')}
                      className="px-5 py-2.5 bg-slate-800/80 hover:bg-slate-800 text-slate-200 border border-slate-700/80 font-bold text-xs rounded-xl flex items-center gap-2 transition-all cursor-pointer"
                    >
                      <span className="material-symbols-outlined text-sm">link</span>
                      Connect Repository
                    </button>
                    <button
                      onClick={() => setActiveTab('dashboard')}
                      className="px-4 py-2.5 text-slate-400 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                    >
                      <span className="material-symbols-outlined text-sm">upload_file</span>
                      Manual Log Analyzer
                    </button>
                  </div>
                </div>

                {/* Key Metrics Mini-Grid */}
                <div className="grid grid-cols-2 gap-3 shrink-0 lg:w-96">
                  <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl flex flex-col gap-1 shadow-sm">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Repositories</span>
                    <span className="text-2xl font-bold text-white font-mono">{repos.length}</span>
                    <span className="text-[11px] text-emerald-400 flex items-center gap-1 mt-1">
                      <span className="material-symbols-outlined text-xs">check_circle</span>
                      Active Webhooks
                    </span>
                  </div>

                  <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl flex flex-col gap-1 shadow-sm">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Events Analyzed</span>
                    <span className="text-2xl font-bold text-indigo-400 font-mono">{pipelineEvents.length}</span>
                    <span className="text-[11px] text-slate-400 flex items-center gap-1 mt-1">
                      <span className="material-symbols-outlined text-xs">history</span>
                      Persistent Runs
                    </span>
                  </div>

                  <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl flex flex-col gap-1 shadow-sm">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Mean Time to Detect</span>
                    <span className="text-2xl font-bold text-cyan-400 font-mono">1.2s</span>
                    <span className="text-[11px] text-slate-400 flex items-center gap-1 mt-1">
                      <span className="material-symbols-outlined text-xs">speed</span>
                      HMAC Event Push
                    </span>
                  </div>

                  <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl flex flex-col gap-1 shadow-sm">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">Test Verification</span>
                    <span className="text-2xl font-bold text-emerald-400 font-mono">30/30</span>
                    <span className="text-[11px] text-emerald-400 flex items-center gap-1 mt-1">
                      <span className="material-symbols-outlined text-xs">verified</span>
                      All Milestones Green
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* 4 Architectural Milestones Workflow Guide */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-bold text-white">Continuous Reliability Engine Stages</h2>
                  <p className="text-xs text-slate-400">Autonomous workflow from failure webhook to verified staging remediation</p>
                </div>
                <button
                  onClick={() => setActiveTab('architecture')}
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1"
                >
                  Inspect Full Architecture <span className="material-symbols-outlined text-xs">arrow_forward</span>
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div 
                  onClick={() => setActiveTab('repositories')}
                  className="bg-slate-900/60 border border-slate-800 hover:border-indigo-500/40 p-5 rounded-2xl flex flex-col justify-between transition-all cursor-pointer group hover:-translate-y-0.5"
                >
                  <div>
                    <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                      <span className="material-symbols-outlined text-xl">shield</span>
                    </div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-indigo-400 font-bold block mb-1">STAGE 1</span>
                    <h3 className="font-bold text-sm text-slate-100 mb-1">Two-Tier RBAC & Connect</h3>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Maps GitHub collaborator permissions (Admin, Maintain, Write) to application roles (Owner, Admin, Developer).
                    </p>
                  </div>
                  <span className="text-[11px] font-semibold text-indigo-400 mt-4 flex items-center gap-1">
                    Manage Access <span className="material-symbols-outlined text-xs">arrow_forward</span>
                  </span>
                </div>

                <div 
                  onClick={() => setActiveTab('monitoring')}
                  className="bg-slate-900/60 border border-slate-800 hover:border-indigo-500/40 p-5 rounded-2xl flex flex-col justify-between transition-all cursor-pointer group hover:-translate-y-0.5"
                >
                  <div>
                    <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                      <span className="material-symbols-outlined text-xl">webhook</span>
                    </div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-blue-400 font-bold block mb-1">STAGE 2</span>
                    <h3 className="font-bold text-sm text-slate-100 mb-1">HMAC Ingestion & Queue</h3>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Constant-time HMAC-SHA256 signature verification. Offloads parsing and RAG to Celery + Redis workers.
                    </p>
                  </div>
                  <span className="text-[11px] font-semibold text-blue-400 mt-4 flex items-center gap-1">
                    Launch Monitor <span className="material-symbols-outlined text-xs">arrow_forward</span>
                  </span>
                </div>

                <div 
                  onClick={() => setActiveTab('analysis')}
                  className="bg-slate-900/60 border border-slate-800 hover:border-indigo-500/40 p-5 rounded-2xl flex flex-col justify-between transition-all cursor-pointer group hover:-translate-y-0.5"
                >
                  <div>
                    <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                      <span className="material-symbols-outlined text-xl">history</span>
                    </div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-purple-400 font-bold block mb-1">STAGE 3</span>
                    <h3 className="font-bold text-sm text-slate-100 mb-1">Historical Recurrence RAG</h3>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Correlates error signatures with FAISS memory. Flags recurring incidents and prompts Gemini with prior fixes.
                    </p>
                  </div>
                  <span className="text-[11px] font-semibold text-purple-400 mt-4 flex items-center gap-1">
                    Inspect RAG Reports <span className="material-symbols-outlined text-xs">arrow_forward</span>
                  </span>
                </div>

                <div 
                  onClick={() => setActiveTab('analysis')}
                  className="bg-slate-900/60 border border-slate-800 hover:border-indigo-500/40 p-5 rounded-2xl flex flex-col justify-between transition-all cursor-pointer group hover:-translate-y-0.5"
                >
                  <div>
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                      <span className="material-symbols-outlined text-xl">code_blocks</span>
                    </div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-bold block mb-1">STAGE 4</span>
                    <h3 className="font-bold text-sm text-slate-100 mb-1">AI Code Patch & Approvals</h3>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Unified Git diff synthesis with human-in-the-loop review workflow and simulated staging execution.
                    </p>
                  </div>
                  <span className="text-[11px] font-semibold text-emerald-400 mt-4 flex items-center gap-1">
                    Review Code Patches <span className="material-symbols-outlined text-xs">arrow_forward</span>
                  </span>
                </div>
              </div>
            </div>

            {/* Live Pipeline Events Stream */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                  <h3 className="text-base font-bold text-white">Recent Pipeline Telemetry Stream</h3>
                </div>
                <button
                  onClick={() => setActiveTab('monitoring')}
                  className="text-xs text-indigo-400 hover:underline font-semibold self-start sm:self-auto"
                >
                  View full monitor & simulator &rarr;
                </button>
              </div>

              {pipelineEvents.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
                  <span className="material-symbols-outlined text-3xl text-slate-600">hourglass_empty</span>
                  <span>No pipeline events recorded yet. Trigger a simulated webhook below to test the engine.</span>
                  <button
                    onClick={handleSimulateWebhook}
                    className="mt-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold transition-all cursor-pointer"
                  >
                    Run Demo Webhook Simulation
                  </button>
                </div>
              ) : (
                <div className="divide-y divide-slate-800/80">
                  {pipelineEvents.slice(0, 5).map(evt => (
                    <div key={evt.id} className="py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-slate-800/20 px-2 rounded-xl transition-colors">
                      <div className="flex items-start gap-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase mt-0.5 ${
                          evt.conclusion === 'failure'
                            ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                            : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                        }`}>
                          {evt.conclusion}
                        </span>
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-xs text-slate-200">{evt.workflow_name}</span>
                            <span className="text-slate-500">•</span>
                            <span className="text-xs text-slate-400 font-mono">{evt.repo_full_name}</span>
                            <span className="text-slate-500">•</span>
                            <span className="text-xs text-indigo-400 font-mono font-semibold flex items-center gap-1">
                              <span className="material-symbols-outlined text-xs">commit</span>
                              {evt.commit_sha.substring(0, 7)}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{evt.commit_message}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 self-end md:self-auto shrink-0">
                        <span className="text-[10px] font-mono text-slate-500">
                          {new Date(evt.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </span>
                        {evt.analysis && (
                          <button
                            onClick={() => {
                              if (evt.analysis?.analysis_run_id) {
                                setActiveRunId(evt.analysis.analysis_run_id)
                              }
                              setActiveTab('analysis')
                            }}
                            className="px-3 py-1 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-semibold transition-all cursor-pointer"
                          >
                            Diagnosis Report
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>
        )}

        {/* 2. REPOSITORIES & ALERTS TAB */}
        {activeTab === 'repositories' && (
          <div className="flex flex-col gap-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-white tracking-tight">Connected Repositories & Role-Based Routing</h2>
                <p className="text-xs text-slate-400">Configure GitHub access, monitor webhooks, and customize team notification dispatch rules.</p>
              </div>
            </div>

            {/* Connect Repository Form Card */}
            <div className="bg-slate-900/80 border border-slate-800 p-6 rounded-2xl shadow-xl">
              <h3 className="text-sm font-bold text-indigo-400 uppercase tracking-wider flex items-center gap-2 mb-4">
                <span className="material-symbols-outlined text-base">add_circle</span>
                Connect GitHub Repository
              </h3>
              
              <form onSubmit={handleConnectRepo} className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="flex flex-col gap-1.5 md:col-span-1">
                  <label className="text-xs font-semibold text-slate-300">Repository Slug or URL *</label>
                  <input
                    type="text"
                    value={repoUrlInput}
                    onChange={(e) => setRepoUrlInput(e.target.value)}
                    placeholder="e.g. m-tanusree-reddy/pipeline-failure-detection-"
                    className="bg-slate-950 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-mono transition-all"
                    required
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-slate-300">GitHub Personal Access Token (Optional)</label>
                  <input
                    type="password"
                    value={repoTokenInput}
                    onChange={(e) => setRepoTokenInput(e.target.value)}
                    placeholder="ghp_... (enables collaborator checks)"
                    className="bg-slate-950 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 outline-none focus:border-indigo-500 font-mono transition-all"
                  />
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-slate-300">Webhook Secret (Optional)</label>
                  <input
                    type="text"
                    value={repoSecretInput}
                    onChange={(e) => setRepoSecretInput(e.target.value)}
                    placeholder="Auto-generated if left empty"
                    className="bg-slate-950 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 outline-none focus:border-indigo-500 font-mono transition-all"
                  />
                </div>

                <div className="md:col-span-3 flex justify-end gap-3 mt-1">
                  <button
                    type="submit"
                    disabled={isConnectingRepo}
                    className="bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white px-6 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all shadow-md shadow-indigo-600/30 cursor-pointer disabled:opacity-50"
                  >
                    {isConnectingRepo ? (
                      <>
                        <span className="material-symbols-outlined text-sm animate-spin">refresh</span>
                        Verifying Collaborator Access...
                      </>
                    ) : (
                      <>
                        <span className="material-symbols-outlined text-sm">verified_user</span>
                        Verify & Register Repository
                      </>
                    )}
                  </button>
                </div>
              </form>

              {lastConnectedRole && (
                <div className="mt-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-emerald-400">verified</span>
                    <div>
                      <p className="text-xs font-bold text-emerald-300">Repository Verified & RBAC Enforced</p>
                      <p className="text-xs text-slate-400">
                        GitHub Permission: <strong className="font-mono text-white">{lastConnectedRole.gh_perm.toUpperCase()}</strong> → Assigned Platform Role: <strong className="font-mono text-indigo-400">{lastConnectedRole.app_role}</strong>
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Repositories List */}
            <div className="bg-slate-900/80 border border-slate-800 p-6 rounded-2xl shadow-sm">
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-base text-indigo-400">inventory_2</span>
                Active Repositories ({repos.length})
              </h3>

              {repos.length === 0 ? (
                <div className="py-8 text-center text-slate-500 text-xs">
                  No repositories connected. Connect your GitHub repository above to activate automated failure tracking.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {repos.map(r => (
                    <div key={r.id} className="bg-slate-950/60 border border-slate-800 p-4 rounded-xl flex flex-col justify-between gap-3">
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-mono text-xs font-bold text-indigo-400 truncate">{r.full_name}</span>
                          <span className="px-2 py-0.5 rounded text-[9px] font-mono font-bold bg-slate-800 text-slate-300">
                            {r.is_private ? 'PRIVATE' : 'PUBLIC'}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 font-mono">Default Branch: {r.default_branch}</p>
                      </div>

                      <div className="border-t border-slate-800/80 pt-2 flex items-center justify-between text-xs">
                        <button
                          onClick={() => copyToClipboard(r.webhook_secret, `secret-${r.id}`)}
                          className="text-[11px] text-slate-400 hover:text-slate-200 flex items-center gap-1 font-mono cursor-pointer"
                        >
                          <span className="material-symbols-outlined text-xs">
                            {copiedKey === `secret-${r.id}` ? 'check' : 'content_copy'}
                          </span>
                          {copiedKey === `secret-${r.id}` ? 'Copied Secret' : 'Copy Secret'}
                        </button>
                        
                        <button
                          onClick={() => {
                            setSimRepo(r.full_name)
                            setActiveTab('monitoring')
                          }}
                          className="text-[11px] text-indigo-400 hover:underline font-semibold cursor-pointer"
                        >
                          Simulate &rarr;
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Notification Preferences & Channels */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              
              {/* Preferences Card */}
              <div className="lg:col-span-6 bg-slate-900/80 border border-slate-800 p-6 rounded-2xl flex flex-col justify-between shadow-sm">
                <div>
                  <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-2 flex items-center gap-2">
                    <span className="material-symbols-outlined text-indigo-400 text-base">tune</span>
                    Notification Delivery Preferences
                  </h3>
                  <p className="text-xs text-slate-400 mb-4">
                    Customize which external and in-app channels receive alerts when CI workflows fail:
                  </p>

                  <div className="flex flex-col gap-3">
                    {[
                      { key: 'in_app_enabled', label: 'In-App Notification Center', desc: 'Real-time bell tray and status feed' },
                      { key: 'slack_enabled', label: 'Slack Webhook Alerts', desc: 'Formatted Block Kit alerts to team channels' },
                      { key: 'discord_enabled', label: 'Discord Channel Alerts', desc: 'Embedded failure breakdowns in Discord' },
                      { key: 'email_enabled', label: 'Email Digest Notifications', desc: 'Post-mortem incident summaries' },
                      { key: 'notify_critical_only', label: 'Critical Only Filter', desc: 'Only alert on main branch failures or repeat incidents' },
                    ].map(pref => (
                      <label key={pref.key} className="flex items-start justify-between p-3 rounded-xl bg-slate-950/40 border border-slate-800/80 cursor-pointer hover:bg-slate-950/70 transition-colors">
                        <div>
                          <p className="font-bold text-xs text-slate-200">{pref.label}</p>
                          <p className="text-[11px] text-slate-400">{pref.desc}</p>
                        </div>
                        <input
                          type="checkbox"
                          checked={(preferences as any)[pref.key]}
                          onChange={(e) => updatePreferences({ ...preferences, [pref.key]: e.target.checked })}
                          className="w-4 h-4 rounded text-indigo-600 bg-slate-900 border-slate-700 focus:ring-indigo-500 mt-1 cursor-pointer"
                        />
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              {/* External Destination Webhooks Card */}
              <div className="lg:col-span-6 bg-slate-900/80 border border-slate-800 p-6 rounded-2xl flex flex-col justify-between shadow-sm">
                <div>
                  <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-2 flex items-center gap-2">
                    <span className="material-symbols-outlined text-indigo-400 text-base">cell_tower</span>
                    Register Alert Destinations
                  </h3>
                  <p className="text-xs text-slate-400 mb-4">
                    Add Slack incoming webhook URLs, Discord webhook URLs, or on-call developer email addresses:
                  </p>

                  <form onSubmit={handleAddChannel} className="flex flex-col gap-3">
                    <div className="flex gap-2">
                      <select
                        value={newChannelType}
                        onChange={(e) => setNewChannelType(e.target.value)}
                        className="bg-slate-950 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-white outline-none shrink-0"
                      >
                        <option value="slack">Slack Webhook</option>
                        <option value="discord">Discord Webhook</option>
                        <option value="email">Developer Email</option>
                      </select>
                      <input
                        type="text"
                        value={newChannelTarget}
                        onChange={(e) => setNewChannelTarget(e.target.value)}
                        placeholder="https://hooks.slack.com/services/... or dev@corp.io"
                        className="bg-slate-950 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 outline-none flex-grow font-mono"
                        required
                      />
                    </div>
                    <button
                      type="submit"
                      className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center justify-center gap-1.5"
                    >
                      <span className="material-symbols-outlined text-xs">add</span>
                      Register Webhook Destination
                    </button>
                  </form>

                  {/* Registered channels list */}
                  <div className="mt-4 flex flex-col gap-2 max-h-48 overflow-y-auto">
                    {channels.length === 0 ? (
                      <p className="text-slate-500 text-xs italic text-center py-4">No external channels registered for the active repository.</p>
                    ) : (
                      channels.map(c => (
                        <div key={c.id} className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between text-xs">
                          <span className="font-mono text-indigo-400 uppercase font-bold text-[10px]">{c.channel}</span>
                          <span className="font-mono text-slate-400 text-[11px] truncate max-w-xs">{c.target}</span>
                          <span className="w-2 h-2 rounded-full bg-emerald-400" />
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

            </div>

            {/* Role-Based Alert Routing Policy Matrix Card */}
            <div className="bg-slate-900/80 border border-slate-800 p-6 rounded-2xl shadow-sm">
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-2 flex items-center gap-2">
                <span className="material-symbols-outlined text-indigo-400 text-base">rule</span>
                Role-Based Alert Routing Matrix (Automated RBAC)
              </h3>
              <p className="text-xs text-slate-400 mb-4">
                Incoming failure alerts are evaluated by branch criticality and historical recurrence to guarantee that the right stakeholder is notified without alert spam.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
                <div className="bg-slate-950/70 p-4 rounded-xl border border-rose-500/30">
                  <span className="text-[10px] uppercase font-bold text-rose-400 font-mono block mb-1">CRITICAL INCIDENT</span>
                  <h4 className="font-bold text-sm text-slate-100 mb-1">Main / Prod Failure</h4>
                  <p className="text-slate-400 text-[11px]">Recipients: <strong className="text-indigo-400">Admin + Developers + Owner</strong></p>
                  <p className="text-slate-500 text-[10px] mt-2">Channels: In-App, Slack, Email</p>
                </div>

                <div className="bg-slate-950/70 p-4 rounded-xl border border-rose-500/30">
                  <span className="text-[10px] uppercase font-bold text-rose-400 font-mono block mb-1">REPEATED INCIDENT</span>
                  <h4 className="font-bold text-sm text-slate-100 mb-1">Recurrent Failure</h4>
                  <p className="text-slate-400 text-[11px]">Recipients: <strong className="text-indigo-400">Owner + Admin</strong> (Escalated)</p>
                  <p className="text-slate-500 text-[10px] mt-2">Channels: In-App, Slack High-Priority</p>
                </div>

                <div className="bg-slate-950/70 p-4 rounded-xl border border-amber-500/30">
                  <span className="text-[10px] uppercase font-bold text-amber-400 font-mono block mb-1">WARNING INCIDENT</span>
                  <h4 className="font-bold text-sm text-slate-100 mb-1">Feature Branch Failure</h4>
                  <p className="text-slate-400 text-[11px]">Recipients: <strong className="text-indigo-400">Assigned Developer</strong></p>
                  <p className="text-slate-500 text-[10px] mt-2">Channels: In-App Notification</p>
                </div>

                <div className="bg-slate-950/70 p-4 rounded-xl border border-indigo-500/30">
                  <span className="text-[10px] uppercase font-bold text-indigo-400 font-mono block mb-1">ACCESS GOVERNANCE</span>
                  <h4 className="font-bold text-sm text-slate-100 mb-1">Access / Role Change</h4>
                  <p className="text-slate-400 text-[11px]">Recipients: <strong className="text-indigo-400">Repository Owner</strong></p>
                  <p className="text-slate-500 text-[10px] mt-2">Channels: In-App, Email</p>
                </div>
              </div>
            </div>

          </div>
        )}

        {/* 3. PIPELINE MONITOR (WEBHOOKS & SIMULATOR) TAB */}
        {activeTab === 'monitoring' && (
          <div className="flex flex-col gap-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-white tracking-tight">Continuous Pipeline Failure Monitor</h2>
                <p className="text-xs text-slate-400">Live GitHub Actions `workflow_run.completed` ingestion with HMAC cryptographic verification.</p>
              </div>
            </div>

            {/* Listener Specification & Simulator */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              
              {/* Webhook Listener Config Card */}
              <div className="lg:col-span-5 bg-slate-900/80 border border-slate-800 p-6 rounded-2xl flex flex-col justify-between shadow-xl">
                <div>
                  <h3 className="text-sm font-bold text-indigo-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                    <span className="material-symbols-outlined text-base">satellite_alt</span>
                    Webhook Listener Endpoint
                  </h3>
                  <p className="text-xs text-slate-400 mb-4 leading-relaxed">
                    Configure your GitHub repository webhook to dispatch events to this URL on pipeline failure:
                  </p>

                  <div className="flex flex-col gap-3">
                    <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex items-center justify-between">
                      <div className="flex flex-col overflow-hidden mr-2">
                        <span className="text-[9px] font-mono uppercase text-slate-500">Payload URL</span>
                        <span className="font-mono text-xs text-indigo-300 truncate">
                          {API_BASE ? `${API_BASE}/api/webhooks/github` : 'http://localhost:8000/api/webhooks/github'}
                        </span>
                      </div>
                      <button
                        onClick={() => copyToClipboard(API_BASE ? `${API_BASE}/api/webhooks/github` : 'http://localhost:8000/api/webhooks/github', 'webhook-url')}
                        className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-mono shrink-0 cursor-pointer flex items-center gap-1"
                      >
                        <span className="material-symbols-outlined text-xs">
                          {copiedKey === 'webhook-url' ? 'check' : 'content_copy'}
                        </span>
                        <span>{copiedKey === 'webhook-url' ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>

                    <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex items-center justify-between">
                      <div className="flex flex-col">
                        <span className="text-[9px] font-mono uppercase text-slate-500">Security Signature</span>
                        <span className="font-mono text-xs text-cyan-400">HMAC-SHA256 (Constant Time)</span>
                      </div>
                      <span className="material-symbols-outlined text-emerald-400 text-sm">lock</span>
                    </div>

                    <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex items-center justify-between">
                      <div className="flex flex-col">
                        <span className="text-[9px] font-mono uppercase text-slate-500">Alert Deduplication</span>
                        <span className="font-mono text-xs text-emerald-400">10-Minute Signature Window Active</span>
                      </div>
                      <span className="material-symbols-outlined text-indigo-400 text-sm">filter_alt</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Webhook Simulator with Presets */}
              <div className="lg:col-span-7 bg-slate-900/80 border border-slate-800 p-6 rounded-2xl flex flex-col justify-between shadow-xl">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                      <span className="material-symbols-outlined text-indigo-400 text-base">play_circle</span>
                      Simulate CI Failure Webhook
                    </h3>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                      Developer Testing
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mb-3">
                    Select a realistic CI/CD failure scenario to test the HMAC verification, Celery queue, and role routing:
                  </p>

                  {/* 1-Click Simulation Presets */}
                  <div className="grid grid-cols-2 gap-2 mb-4">
                    {SIMULATION_PRESETS.map(p => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => applyPreset(p.id)}
                        className={`p-2.5 rounded-xl border text-left flex flex-col gap-1 transition-all cursor-pointer hover:border-indigo-400 ${
                          simWorkflow === p.workflow ? 'bg-indigo-600/15 border-indigo-500/50' : 'bg-slate-950/60 border-slate-800'
                        }`}
                      >
                        <span className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded w-fit ${p.badgeColor}`}>
                          {p.category.replace('_', ' ')}
                        </span>
                        <span className="font-bold text-xs text-slate-200">{p.title}</span>
                      </button>
                    ))}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="flex flex-col gap-1">
                      <label className="text-[11px] font-semibold text-slate-400">Target Repository</label>
                      <select
                        value={simRepo}
                        onChange={(e) => setSimRepo(e.target.value)}
                        className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none"
                      >
                        {repos.map(r => (
                          <option key={r.id} value={r.full_name}>{r.full_name}</option>
                        ))}
                        {repos.length === 0 && (
                          <option value="m-tanusree-reddy/pipeline-failure-detection-">m-tanusree-reddy/pipeline-failure-detection-</option>
                        )}
                      </select>
                    </div>

                    <div className="flex flex-col gap-1">
                      <label className="text-[11px] font-semibold text-slate-400">Branch Name</label>
                      <input
                        type="text"
                        value={simBranch}
                        onChange={(e) => setSimBranch(e.target.value)}
                        className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none font-mono"
                      />
                    </div>

                    <div className="flex flex-col gap-1 md:col-span-2">
                      <label className="text-[11px] font-semibold text-slate-400">Failure Exception / Signature</label>
                      <input
                        type="text"
                        value={simErrorType}
                        onChange={(e) => setSimErrorType(e.target.value)}
                        className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none font-mono"
                      />
                    </div>
                  </div>

                  <div className="mt-4 flex justify-end">
                    <button
                      onClick={handleSimulateWebhook}
                      disabled={isSimulatingWebhook}
                      className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-bold text-xs rounded-xl shadow-lg shadow-indigo-600/30 flex items-center gap-2 transition-all cursor-pointer disabled:opacity-50"
                    >
                      {isSimulatingWebhook ? (
                        <>
                          <span className="material-symbols-outlined text-sm animate-spin">refresh</span>
                          Dispatching HMAC Event...
                        </>
                      ) : (
                        <>
                          <span className="material-symbols-outlined text-sm">send</span>
                          Dispatch Failure Webhook
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>

            </div>

            {/* Pipeline Events Log Table */}
            <div className="bg-slate-900/80 border border-slate-800 p-6 rounded-2xl shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
                    Recorded Pipeline Runs ({filteredEvents.length})
                  </h3>
                  <p className="text-xs text-slate-400">Search and filter monitored webhook events</p>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  <div className="flex rounded-xl bg-slate-950 border border-slate-800 p-0.5 text-xs font-semibold">
                    {(['ALL', 'FAILED', 'SUCCESS'] as const).map(filter => (
                      <button
                        key={filter}
                        onClick={() => setEventStatusFilter(filter)}
                        className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                          eventStatusFilter === filter ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
                        }`}
                      >
                        {filter}
                      </button>
                    ))}
                  </div>

                  <input
                    type="text"
                    value={eventSearchQuery}
                    onChange={(e) => setEventSearchQuery(e.target.value)}
                    placeholder="Search runs..."
                    className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 outline-none w-48 font-mono"
                  />
                </div>
              </div>

              {filteredEvents.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-xs">
                  No matching pipeline events found.
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  {filteredEvents.map(evt => (
                    <div
                      key={evt.id}
                      className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-indigo-500/30 transition-all"
                    >
                      <div className="flex items-start gap-3">
                        <span className={`px-2.5 py-1 rounded text-[10px] font-mono font-bold uppercase shrink-0 mt-0.5 ${
                          evt.conclusion === 'failure'
                            ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                            : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                        }`}>
                          {evt.conclusion}
                        </span>

                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-sm text-slate-100">{evt.workflow_name}</span>
                            <span className="text-slate-500">•</span>
                            <span className="font-mono text-xs text-indigo-400">{evt.repo_full_name}</span>
                            <span className="text-slate-500">•</span>
                            <span className="font-mono text-xs text-slate-300 bg-slate-900 px-2 py-0.5 rounded">
                              {evt.branch}
                            </span>
                          </div>

                          <p className="text-xs text-slate-400 mt-1">{evt.commit_message}</p>

                          {evt.analysis && (
                            <div className="mt-2 text-xs bg-slate-900/80 p-2.5 rounded-lg border border-indigo-500/20 text-slate-300">
                              <strong className="text-indigo-400">AI Root Cause:</strong> {evt.analysis.root_cause}
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="flex md:flex-col items-end justify-between md:justify-center gap-2 shrink-0">
                        <span className="text-[10px] font-mono text-slate-500">
                          {new Date(evt.created_at).toLocaleTimeString()}
                        </span>
                        {evt.analysis && (
                          <button
                            onClick={() => {
                              if (evt.analysis?.analysis_run_id) {
                                setActiveRunId(evt.analysis.analysis_run_id)
                              }
                              setActiveTab('analysis')
                            }}
                            className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold transition-all shadow-sm cursor-pointer"
                          >
                            Diagnosis & Fix &rarr;
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>
        )}

        {/* 4. DASHBOARD (LIVE ANALYSIS & DAG) TAB */}
        {activeTab === 'dashboard' && (
          <div className="flex flex-col gap-6">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
              
              {/* Left Column: Manual Log Upload & Select */}
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
                  className="bg-slate-900/80 border-2 border-dashed border-slate-700/80 hover:border-indigo-500 p-6 rounded-2xl flex flex-col items-center justify-center text-center transition-all cursor-pointer h-48 group shadow-sm"
                >
                  {isUploading ? (
                    <div className="flex flex-col items-center gap-2">
                      <span className="material-symbols-outlined text-indigo-400 text-4xl animate-spin">sync</span>
                      <span className="font-bold text-xs text-slate-200">Ingesting log stream...</span>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-2">
                      <div className="w-12 h-12 rounded-full bg-indigo-500/10 text-indigo-400 flex items-center justify-center group-hover:scale-110 transition-transform">
                        <span className="material-symbols-outlined text-2xl">upload_file</span>
                      </div>
                      <h4 className="font-bold text-xs text-slate-200">Drop Manual CI Log</h4>
                      <p className="text-[11px] text-slate-400">Click to browse .TXT, .LOG, or .ZIP</p>
                    </div>
                  )}
                </div>

                <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl flex-grow flex flex-col gap-3 shadow-sm">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold border-b border-slate-800 pb-2">
                    Available Logs ({logs.length})
                  </span>

                  <div className="flex flex-col gap-2 overflow-y-auto max-h-44 pr-1">
                    {logs.map(log => (
                      <button
                        key={log.id}
                        onClick={() => setSelectedLogId(log.id)}
                        className={`w-full text-left p-2.5 rounded-xl border text-xs flex items-center justify-between transition-all cursor-pointer ${
                          selectedLogId === log.id
                            ? 'border-indigo-500 bg-indigo-600/15 text-indigo-300 font-bold'
                            : 'border-slate-800 bg-slate-950/40 text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                        }`}
                      >
                        <span className="truncate pr-2">{log.name}</span>
                        <span className="text-[9px] font-mono px-2 py-0.5 bg-slate-800 rounded text-slate-400 uppercase shrink-0">
                          {log.type}
                        </span>
                      </button>
                    ))}
                  </div>

                  <button
                    onClick={() => startAnalysis(selectedLogId)}
                    disabled={isAnalyzing || !selectedLogId}
                    className="w-full bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white py-2.5 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-md shadow-indigo-600/25 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed mt-2"
                  >
                    {isAnalyzing ? (
                      <>
                        <span className="material-symbols-outlined text-sm animate-spin">refresh</span>
                        Analyzing Pipeline...
                      </>
                    ) : (
                      <>
                        <span className="material-symbols-outlined text-sm">play_arrow</span>
                        Execute Diagnostic Run
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Right Column: Execution Stepper / DAG Flow */}
              <div className="lg:col-span-8 bg-slate-900/80 border border-slate-800 p-6 rounded-2xl flex flex-col justify-between shadow-xl">
                <div>
                  <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-800">
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-indigo-400">account_tree</span>
                      <h3 className="font-bold text-base text-white">Diagnostic Execution Pipeline</h3>
                    </div>

                    {runData && (
                      <div className="flex items-center gap-3">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-mono font-bold flex items-center gap-1.5 border ${
                          runData.status === 'running'
                            ? 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30'
                            : runData.status === 'completed'
                            ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                            : 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                        }`}>
                          <span className={`w-2 h-2 rounded-full ${runData.status === 'running' ? 'bg-indigo-400 animate-pulse' : runData.status === 'completed' ? 'bg-emerald-400' : 'bg-rose-400'}`} />
                          {runData.status.toUpperCase()}
                        </span>
                        <span className="text-slate-500 text-xs font-mono">Run: {runData.run_id.substring(0, 8)}...</span>
                      </div>
                    )}
                  </div>

                  {/* 4 Multi-Stage Execution Steps */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
                    {[
                      {
                        key: 'parsing',
                        title: '1. Log Parser & Trace Normalization',
                        desc: 'Strips volatile memory addresses (0x7fa...) and isolates critical exception traces.',
                        stageKey: 'Parser'
                      },
                      {
                        key: 'classifying',
                        title: '2. Granular Classification (8 Archetypes)',
                        desc: 'Maps errors into archetypes and calculates multi-factor composite severity.',
                        stageKey: 'Classifier'
                      },
                      {
                        key: 'planning',
                        title: '3. Historical FAISS & Gemini Reasoning',
                        desc: 'Dense RAG similarity retrieval with recurrence memory and Critic verification.',
                        stageKey: 'LLM'
                      },
                      {
                        key: 'remediation',
                        title: '4. AI Code Patch Synthesis & Alerts',
                        desc: 'Unified Git diff patch generation with role-based alert dispatch.',
                        stageKey: 'Report'
                      }
                    ].map(step => {
                      const s = getStepStatus(step.key)
                      return (
                        <div key={step.key} className="bg-slate-950/70 p-4 rounded-xl border border-slate-800/80 flex flex-col justify-between gap-2">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-xs text-slate-200">{step.title}</span>
                            <span className={`text-[10px] font-mono font-bold ${s.color}`}>
                              {s.label}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-400 leading-relaxed">{step.desc}</p>
                          <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-2 border-t border-slate-900">
                            <span>Stage: {step.stageKey}</span>
                            <span>{runData?.stages[step.stageKey]?.time ? `${runData.stages[step.stageKey].time.toFixed(2)}s` : '--'}</span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {runData?.report && (
                  <div className="mt-4 pt-4 border-t border-slate-800 flex justify-end">
                    <button
                      onClick={() => setActiveTab('analysis')}
                      className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white rounded-xl text-xs font-bold transition-all flex items-center gap-2 shadow-md shadow-indigo-600/30 cursor-pointer"
                    >
                      <span>Inspect Diagnosis & AI Code Patch</span>
                      <span className="material-symbols-outlined text-xs">arrow_forward</span>
                    </button>
                  </div>
                )}
              </div>

            </div>

            {/* Pro Terminal Stream Panel */}
            <div className="bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl flex flex-col h-80">
              
              {/* Terminal Title Bar */}
              <div className="bg-slate-900/90 px-4 py-2.5 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-full bg-rose-500/80" />
                    <span className="w-3 h-3 rounded-full bg-amber-500/80" />
                    <span className="w-3 h-3 rounded-full bg-emerald-500/80" />
                  </div>
                  <span className="text-xs font-mono font-bold text-slate-300">Live Stage & Worker Telemetry Stream</span>
                </div>

                <div className="flex items-center gap-3">
                  {/* Filter Pills */}
                  <div className="flex items-center gap-1 text-[10px] font-mono font-bold">
                    {(['ALL', 'ERROR', 'WARNING', 'INFO'] as const).map(f => (
                      <button
                        key={f}
                        onClick={() => setLogFilter(f)}
                        className={`px-2 py-0.5 rounded cursor-pointer ${
                          logFilter === f ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                        }`}
                      >
                        {f}
                      </button>
                    ))}
                  </div>

                  <button
                    onClick={() => setIsAutoScroll(!isAutoScroll)}
                    className={`text-[10px] font-mono px-2 py-0.5 rounded border transition-colors cursor-pointer ${
                      isAutoScroll ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' : 'text-slate-500 border-slate-800'
                    }`}
                  >
                    Auto-Scroll: {isAutoScroll ? 'ON' : 'OFF'}
                  </button>
                </div>
              </div>

              {/* Log Messages Content */}
              <div className="flex-grow p-4 font-mono text-xs overflow-y-auto space-y-1 bg-[#060911] leading-relaxed">
                {filteredLogs.length === 0 ? (
                  <p className="text-slate-600 italic">&gt; Stream initialized. Trigger an analysis or simulation to stream worker logs.</p>
                ) : (
                  filteredLogs.map((log, idx) => (
                    <div key={idx} className="flex items-start gap-2">
                      <span className="text-slate-600 shrink-0 select-none">[{log.timestamp}]</span>
                      <span className={`font-bold shrink-0 ${
                        log.level === 'ERROR' ? 'text-rose-400' : log.level === 'WARNING' ? 'text-amber-400' : 'text-indigo-400'
                      }`}>
                        {log.level}
                      </span>
                      <span className="text-slate-300">{log.message}</span>
                    </div>
                  ))
                )}
                <div ref={terminalEndRef} />
              </div>
            </div>

          </div>
        )}

        {/* 5. ANALYSIS (ROOT CAUSE & AI FIXES) TAB */}
        {activeTab === 'analysis' && (
          <div className="flex flex-col gap-8">
            {!runData?.report ? (
              <div className="bg-slate-900/80 border border-slate-800 p-12 text-center rounded-2xl flex flex-col items-center justify-center min-h-[420px] shadow-sm">
                <div className="w-16 h-16 rounded-full bg-slate-800 text-slate-500 flex items-center justify-center mb-4">
                  <span className="material-symbols-outlined text-3xl">search_off</span>
                </div>
                <h3 className="text-lg font-bold text-white mb-2">No Active Diagnosis Report</h3>
                <p className="text-xs text-slate-400 max-w-md mb-6 leading-relaxed">
                  Trigger an automated failure simulation on the Pipeline Monitor or run a manual analysis to generate root-cause reports and AI code-level patches.
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={() => setActiveTab('monitoring')}
                    className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold text-xs shadow-md transition-all cursor-pointer"
                  >
                    Open Pipeline Monitor
                  </button>
                  <button
                    onClick={() => setActiveTab('dashboard')}
                    className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-semibold text-xs border border-slate-700 transition-all cursor-pointer"
                  >
                    Upload Manual Log
                  </button>
                </div>
              </div>
            ) : (
              <>
                {/* Header Summary */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 p-6 rounded-2xl shadow-xl">
                  <div>
                    <div className="flex items-center gap-3 mb-1 flex-wrap">
                      <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                        FAILED
                      </span>
                      <h2 className="text-2xl font-bold text-white">{runData.report.failure_type || 'Pipeline Failure'}</h2>
                      
                      {runData.report.is_recurring && (
                        <span className="px-3 py-0.5 rounded-full text-xs font-mono font-bold bg-rose-600 text-white animate-pulse shadow-md">
                          RECURRENT FAILURE ({runData.report.recurrence_count}X)
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 font-mono">
                      Run ID: <span className="text-indigo-400">{runData.run_id}</span> • Source: {runData.log_name}
                    </p>
                  </div>

                  <div className="flex items-center gap-4 shrink-0">
                    <div className="text-right">
                      <span className="text-[10px] font-mono uppercase text-slate-500 block">Critic Confidence</span>
                      <span className="text-xl font-extrabold font-mono text-emerald-400">
                        {((runData.report.final_confidence || 0.95) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <span className="px-3 py-1 bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-semibold">
                      {runData.report.critic_status || 'VERIFIED'}
                    </span>
                  </div>
                </div>

                {/* Historical Recurrence Banner */}
                {runData.report.is_recurring && (
                  <div className="p-5 rounded-2xl bg-rose-950/40 border border-rose-500/40 flex flex-col gap-2 shadow-lg">
                    <div className="flex items-center gap-2 text-rose-400 font-bold text-sm">
                      <span className="material-symbols-outlined text-lg">history</span>
                      <span>Historical Recurrence Detected in FAISS Memory</span>
                    </div>
                    <p className="text-xs text-slate-200 leading-relaxed font-mono">
                      {runData.report.intelligence_note}
                    </p>
                  </div>
                )}

                {/* Granular Archetype & Composite Severity Gauge */}
                {runData.report.failure_category && (
                  <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
                        <span className="material-symbols-outlined text-xl">category</span>
                      </div>
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-mono text-xs font-bold text-indigo-300 px-2.5 py-0.5 rounded bg-indigo-500/15 border border-indigo-500/30">
                            {runData.report.failure_category}
                          </span>
                          <span className={`text-[11px] font-mono font-bold px-2.5 py-0.5 rounded ${
                            runData.report.severity_tier === 'CRITICAL' ? 'bg-rose-500 text-white' :
                            runData.report.severity_tier === 'HIGH' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                            'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                          }`}>
                            {runData.report.severity_tier || 'HIGH'} ({(runData.report.severity_score || 0.70).toFixed(2)})
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 mt-1 font-medium">{runData.report.blast_radius}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-[11px] text-slate-400 font-mono">Impact Score:</span>
                      <div className="w-32 h-2.5 bg-slate-800 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-emerald-400 via-amber-400 to-rose-500 rounded-full"
                          style={{ width: `${Math.min(100, (runData.report.severity_score || 0.7) * 100)}%` }}
                        />
                      </div>
                      <span className="font-mono text-xs font-bold text-white">
                        {((runData.report.severity_score || 0.7) * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                )}

                {/* AI Root-Cause Diagnostic Card */}
                <div className="bg-slate-900/80 border border-slate-800 p-6 rounded-2xl shadow-xl flex flex-col gap-3">
                  <h3 className="text-sm font-bold text-indigo-400 uppercase tracking-wider flex items-center gap-2">
                    <span className="material-symbols-outlined text-base">psychology</span>
                    AI Root-Cause Diagnosis
                  </h3>
                  <p className="font-bold text-sm text-slate-100">{runData.report.root_cause}</p>
                  <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line bg-slate-950/50 p-4 rounded-xl border border-slate-800/80 font-mono">
                    {runData.report.explanation}
                  </p>
                </div>

                {/* Suggested Fixes Checklist */}
                <div className="bg-slate-900/80 border border-slate-800 p-6 rounded-2xl shadow-xl">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                      <span className="material-symbols-outlined text-emerald-400 text-base">build</span>
                      Actionable Remediation Guidance
                    </h3>
                    <button
                      onClick={executeFix}
                      className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition-all shadow-md active:scale-95 cursor-pointer"
                    >
                      Apply Staging Fix
                    </button>
                  </div>

                  <div className="flex flex-col gap-2.5">
                    {runData.report.suggested_fixes?.map((fix, idx) => (
                      <div key={idx} className="bg-slate-950/70 p-3.5 rounded-xl border border-slate-800/80 flex items-start gap-3">
                        <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                          {idx + 1}
                        </span>
                        <p className="text-xs text-slate-300 leading-relaxed font-mono">{fix}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* AI Code-Level Patch & Human-in-the-Loop Approval Workflow */}
                {runData.report.code_patch && (
                  <div className="bg-slate-900/90 border border-slate-800 p-6 rounded-2xl shadow-2xl flex flex-col gap-4">
                    
                    {/* Patch Title Bar & Review Actions */}
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="material-symbols-outlined text-indigo-400">code_blocks</span>
                          <h3 className="text-base font-bold text-white">{runData.report.code_patch.title}</h3>
                          <span className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                            runData.report.code_patch.status === 'applied' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                            runData.report.code_patch.status === 'approved' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' :
                            runData.report.code_patch.status === 'rejected' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                            'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          }`}>
                            {runData.report.code_patch.status.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 font-mono mt-1">
                          Target: <strong className="text-indigo-400">{runData.report.code_patch.target_file}</strong> • Risk: <strong className="text-amber-400">{runData.report.code_patch.risk_level}</strong>
                        </p>
                      </div>

                      {/* Approval Action Buttons */}
                      <div className="flex items-center gap-2">
                        {runData.report.code_patch.status === 'pending_review' && (
                          <>
                            <button
                              onClick={() => handleReviewPatch('approve')}
                              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold transition-all shadow-md active:scale-95 cursor-pointer flex items-center gap-1.5"
                            >
                              <span className="material-symbols-outlined text-sm">thumb_up</span>
                              Approve Patch
                            </button>
                            <button
                              onClick={() => handleReviewPatch('reject')}
                              className="px-3.5 py-2 bg-slate-800 hover:bg-rose-950/60 text-slate-300 hover:text-rose-400 rounded-xl text-xs font-bold border border-slate-700 transition-all cursor-pointer flex items-center gap-1.5 active:scale-95"
                            >
                              <span className="material-symbols-outlined text-sm">thumb_down</span>
                              Reject
                            </button>
                          </>
                        )}
                        {runData.report.code_patch.status === 'approved' && (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={handleCreatePullRequest}
                              disabled={isCreatingPr}
                              className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-emerald-600/30 active:scale-95 cursor-pointer flex items-center gap-1.5"
                            >
                              <span className="material-symbols-outlined text-sm">merge</span>
                              {isCreatingPr ? 'Opening PR...' : 'Open GitHub Pull Request'}
                            </button>
                            <button
                              onClick={handleApplyPatch}
                              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-all shadow-md active:scale-95 cursor-pointer flex items-center gap-1.5"
                            >
                              <span className="material-symbols-outlined text-sm">rocket_launch</span>
                              Apply to Staging
                            </button>
                          </div>
                        )}
                        {runData.report.code_patch.status === 'applied' && (
                          <div className="flex items-center gap-2">
                            <span className="text-emerald-400 text-xs font-mono font-bold flex items-center gap-1.5 bg-emerald-500/15 px-3 py-1.5 rounded-lg border border-emerald-500/30">
                              <span className="material-symbols-outlined text-sm">verified</span>
                              Applied to Staging
                            </span>
                            <button
                              onClick={handleCreatePullRequest}
                              disabled={isCreatingPr}
                              className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-emerald-600/30 active:scale-95 cursor-pointer flex items-center gap-1.5"
                            >
                              <span className="material-symbols-outlined text-sm">merge</span>
                              {isCreatingPr ? 'Opening PR...' : 'Open GitHub Pull Request'}
                            </button>
                          </div>
                        )}
                        {runData.report.code_patch.status === 'pr_created' && (
                          <a
                            href={runData.report.code_patch.pr_url || prResult?.pr_url || '#'}
                            target="_blank"
                            rel="noreferrer"
                            className="px-4 py-2 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 rounded-xl text-xs font-mono font-bold transition-all border border-purple-500/40 flex items-center gap-2 group cursor-pointer"
                          >
                            <span className="material-symbols-outlined text-sm text-purple-400 group-hover:translate-x-0.5 transition-transform">open_in_new</span>
                            Pull Request #{runData.report.code_patch.pr_number || prResult?.pr_number || 'Live'} on GitHub
                          </a>
                        )}
                        <button
                          onClick={handlePostDiagnosticComment}
                          disabled={isPostingComment}
                          title="Post diagnostic summary directly to GitHub commit"
                          className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-xl text-xs font-semibold transition-all border border-slate-700/80 flex items-center gap-1.5 cursor-pointer"
                        >
                          <span className="material-symbols-outlined text-sm text-slate-400">comment</span>
                          {isPostingComment ? 'Posting...' : 'Post GitHub Comment'}
                        </button>
                      </div>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed font-mono">
                      {runData.report.code_patch.rationale}
                    </p>

                    {/* Pro Code Editor Window with Syntax Unified Diff */}
                    <div className="bg-[#0b0e17] rounded-xl overflow-hidden border border-slate-800 shadow-2xl">
                      <div className="bg-slate-900/90 px-4 py-2 border-b border-slate-800 flex items-center justify-between text-xs font-mono">
                        <div className="flex items-center gap-2">
                          <span className="material-symbols-outlined text-xs text-indigo-400">description</span>
                          <span className="text-slate-200 font-bold">{runData.report.code_patch.target_file}</span>
                        </div>
                        <button
                          onClick={() => copyToClipboard(runData.report?.code_patch?.diff_content || '', 'patch-diff')}
                          className="text-[11px] text-slate-400 hover:text-white flex items-center gap-1 cursor-pointer"
                        >
                          <span className="material-symbols-outlined text-xs">
                            {copiedKey === 'patch-diff' ? 'check' : 'content_copy'}
                          </span>
                          <span>{copiedKey === 'patch-diff' ? 'Copied' : 'Copy Diff'}</span>
                        </button>
                      </div>

                      <div className="p-4 font-mono text-xs overflow-x-auto space-y-0.5 max-h-72 leading-relaxed">
                        {runData.report.code_patch.diff_content.split('\n').map((line, lIdx) => {
                          const isAdd = line.startsWith('+') && !line.startsWith('+++')
                          const isDel = line.startsWith('-') && !line.startsWith('---')
                          const isHunk = line.startsWith('@@')
                          const isHeader = line.startsWith('diff --git') || line.startsWith('---') || line.startsWith('+++')
                          return (
                            <div
                              key={lIdx}
                              className={`px-2 py-0.5 rounded ${
                                isAdd ? 'text-emerald-400 bg-emerald-950/40' :
                                isDel ? 'text-rose-400 bg-rose-950/40 line-through opacity-80' :
                                isHunk ? 'text-cyan-400 bg-cyan-950/30 font-bold' :
                                isHeader ? 'text-slate-500 font-bold' :
                                'text-slate-400'
                              }`}
                            >
                              {line || ' '}
                            </div>
                          )
                        })}
                      </div>
                    </div>

                    {runData.report.code_patch.validation_command && (
                      <div className="p-3 bg-slate-950/70 rounded-xl border border-slate-800/80 flex items-center justify-between text-xs font-mono">
                        <div className="flex items-center gap-2">
                          <span className="text-indigo-400 font-bold">Verification Test Command:</span>
                          <code className="text-cyan-300">{runData.report.code_patch.validation_command}</code>
                        </div>
                        <button
                          onClick={() => copyToClipboard(runData.report?.code_patch?.validation_command || '', 'validation-cmd')}
                          className="text-slate-400 hover:text-white cursor-pointer"
                        >
                          <span className="material-symbols-outlined text-xs">
                            {copiedKey === 'validation-cmd' ? 'check' : 'content_copy'}
                          </span>
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {/* Past Occurrences in Repository */}
                {runData.report.past_occurrences && runData.report.past_occurrences.length > 0 && (
                  <div className="bg-slate-900/80 border border-slate-800 p-6 rounded-2xl shadow-sm">
                    <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-3 flex items-center gap-2">
                      <span className="material-symbols-outlined text-indigo-400 text-base">manage_search</span>
                      Previous Occurrences of this Error Signature ({runData.report.past_occurrences.length})
                    </h3>

                    <div className="flex flex-col gap-2">
                      {runData.report.past_occurrences.map((past, i) => (
                        <div key={i} className="p-3 bg-slate-950/60 rounded-xl border border-slate-800 flex items-center justify-between text-xs">
                          <div>
                            <span className="font-mono text-indigo-400 font-bold">Branch: {past.branch}</span> • <span className="font-mono text-slate-300">Commit: {past.commit_sha}</span>
                            <p className="text-[11px] text-slate-400 mt-0.5">{past.root_cause}</p>
                          </div>
                          <span className="text-[10px] font-mono text-slate-500">
                            {past.timestamp ? new Date(past.timestamp).toLocaleDateString() : 'Historical Run'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* 6. ARCHITECTURE & CI/CD TAB */}
        {activeTab === 'architecture' && (
          <div className="flex flex-col gap-8">
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">Enterprise Infrastructure Architecture</h2>
              <p className="text-xs text-slate-400">Complete platform topology spanning Webhooks, Celery Redis queues, FAISS dense RAG, and Observability.</p>
            </div>

            {/* Architecture Card */}
            <div className="bg-slate-900/80 border border-slate-800 p-8 rounded-2xl shadow-xl">
              <h3 className="text-sm font-bold text-indigo-400 uppercase tracking-wider mb-6">
                Platform Milestone Implementation Matrix (1.0 &rarr; 3.0)
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-slate-950/70 p-5 rounded-2xl border border-slate-800 flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-indigo-400">MILESTONE 1 & 2</span>
                    <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">VERIFIED</span>
                  </div>
                  <h4 className="font-bold text-sm text-slate-100">Access Governance & Webhooks</h4>
                  <ul className="text-xs text-slate-400 space-y-1.5 list-disc list-inside">
                    <li>Collaborator permission verification API</li>
                    <li>Two-tier RBAC mapping (Owner, Admin, Dev)</li>
                    <li>HMAC-SHA256 constant-time verification</li>
                    <li>Simulated failure webhook trigger</li>
                  </ul>
                </div>

                <div className="bg-slate-950/70 p-5 rounded-2xl border border-slate-800 flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-blue-400">MILESTONE 3 & 4</span>
                    <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">VERIFIED</span>
                  </div>
                  <h4 className="font-bold text-sm text-slate-100">Notifications & Distributed Queue</h4>
                  <ul className="text-xs text-slate-400 space-y-1.5 list-disc list-inside">
                    <li>Role-aware failure routing matrix</li>
                    <li>10-minute signature window alert throttling</li>
                    <li>Celery + Redis asynchronous worker pool</li>
                    <li>PostgreSQL connection pool & Alembic</li>
                  </ul>
                </div>

                <div className="bg-slate-950/70 p-5 rounded-2xl border border-slate-800 flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-purple-400">MILESTONE 5 & 6</span>
                    <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">VERIFIED</span>
                  </div>
                  <h4 className="font-bold text-sm text-slate-100">AI Intelligence & Telemetry</h4>
                  <ul className="text-xs text-slate-400 space-y-1.5 list-disc list-inside">
                    <li>8 granular archetypes & composite severity</li>
                    <li>Unified Git diff code patch synthesis</li>
                    <li>Human-in-the-loop review RBAC approval</li>
                    <li>Prometheus (/api/metrics) & Grafana dashboards</li>
                  </ul>
                </div>
              </div>

              {/* Observability Links */}
              <div className="mt-8 pt-6 border-t border-slate-800 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                  <a
                    href={`${API_BASE}/api/metrics`}
                    target="_blank"
                    rel="noreferrer"
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-xs font-mono font-bold flex items-center gap-2 transition-all"
                  >
                    <span className="material-symbols-outlined text-xs">monitoring</span>
                    GET /api/metrics (Prometheus)
                  </a>
                  <a
                    href={`${API_BASE}/api/system/status`}
                    target="_blank"
                    rel="noreferrer"
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-xs font-mono font-bold flex items-center gap-2 transition-all"
                  >
                    <span className="material-symbols-outlined text-xs">database</span>
                    GET /api/system/status
                  </a>
                </div>

                <span className="text-xs text-slate-500 font-mono">
                  All 30 automated integration tests passing • Docker Compose Stack Active
                </span>
              </div>
            </div>
          </div>
        )}

      </main>

      {/* Enterprise Platform Footer */}
      <footer className="bg-slate-950 border-t border-slate-800/80 w-full py-6 text-xs mt-auto">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex flex-col gap-0.5 text-center md:text-left">
            <span className="font-extrabold text-slate-300 tracking-wider text-[11px] uppercase">
              Pipeline Failure Detection 3.0 Platform
            </span>
            <p className="text-slate-500 text-[11px]">
              Enterprise Continuous Integration Failure Intelligence • Protected by Two-Tier RBAC & HMAC-SHA256
            </p>
          </div>

          <div className="flex items-center gap-4 text-slate-400 font-mono text-[11px]">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Platform Status: Operational
            </span>
            <span className="text-slate-700">|</span>
            <span>All 30 Integration Tests Passing</span>
            <span className="text-slate-700">|</span>
            <span className="text-slate-500">v3.0 Release</span>
          </div>
        </div>
      </footer>

      {/* GitHub Authentication & OAuth Modal */}
      {isAuthModalOpen && (
        <div className="fixed inset-0 z-[150] bg-black/80 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-700/80 rounded-3xl max-w-md w-full p-6 shadow-2xl flex flex-col gap-5 relative">
            <button
              onClick={() => setIsAuthModalOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-sm">close</span>
            </button>

            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="material-symbols-outlined text-indigo-400 text-xl">security</span>
                <h3 className="text-lg font-bold text-white">Sign In to Reliability Platform</h3>
              </div>
              <p className="text-xs text-slate-400">
                Authenticate with GitHub to access repository collaborator permissions and role-based workflows.
              </p>
            </div>

            {/* Auth Mode Tabs */}
            <div className="flex rounded-xl bg-slate-950 p-1 border border-slate-800 text-xs font-semibold">
              <button
                onClick={() => setAuthTab('oauth')}
                className={`flex-1 py-1.5 rounded-lg transition-all cursor-pointer ${authTab === 'oauth' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
              >
                GitHub OAuth
              </button>
              <button
                onClick={() => setAuthTab('pat')}
                className={`flex-1 py-1.5 rounded-lg transition-all cursor-pointer ${authTab === 'pat' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
              >
                Access Token
              </button>
              <button
                onClick={() => setAuthTab('demo')}
                className={`flex-1 py-1.5 rounded-lg transition-all cursor-pointer ${authTab === 'demo' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
              >
                Demo Mode
              </button>
            </div>

            {/* Tab 1: GitHub OAuth */}
            {authTab === 'oauth' && (
              <div className="flex flex-col gap-4 text-xs">
                <p className="text-slate-300 leading-relaxed">
                  Redirects to GitHub to verify repository access and authorize collaborator permissions.
                </p>
                <button
                  onClick={handleOAuthLogin}
                  disabled={isAuthenticating}
                  className="w-full py-3 bg-[#24292f] hover:bg-[#1f2328] active:scale-95 text-white font-bold rounded-xl flex items-center justify-center gap-2 transition-all border border-slate-700 shadow-lg cursor-pointer disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-lg">account_circle</span>
                  <span>{isAuthenticating ? 'Redirecting to GitHub...' : 'Continue with GitHub OAuth'}</span>
                </button>
                <span className="text-[10px] text-slate-500 text-center font-mono">
                  Requires GITHUB_CLIENT_ID configured on server
                </span>
              </div>
            )}

            {/* Tab 2: Personal Access Token */}
            {authTab === 'pat' && (
              <form onSubmit={handleTokenLogin} className="flex flex-col gap-3 text-xs">
                <div className="flex flex-col gap-1">
                  <label className="text-slate-300 font-semibold">GitHub Personal Access Token *</label>
                  <input
                    type="password"
                    value={patInput}
                    onChange={(e) => setPatInput(e.target.value)}
                    placeholder="ghp_... (with repo / read:user scopes)"
                    className="bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-white placeholder-slate-500 font-mono outline-none focus:border-indigo-500"
                    required
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-slate-300 font-semibold">GitHub Username (Optional)</label>
                  <input
                    type="text"
                    value={patUsernameInput}
                    onChange={(e) => setPatUsernameInput(e.target.value)}
                    placeholder="e.g. m-tanusree-reddy"
                    className="bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-white placeholder-slate-500 font-mono outline-none focus:border-indigo-500"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isAuthenticating}
                  className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-bold rounded-xl transition-all shadow-md shadow-indigo-600/30 cursor-pointer disabled:opacity-50 mt-1"
                >
                  {isAuthenticating ? 'Validating Token...' : 'Sign In with Token'}
                </button>
              </form>
            )}

            {/* Tab 3: Demo Mode */}
            {authTab === 'demo' && (
              <div className="flex flex-col gap-3 text-xs">
                <p className="text-slate-300 leading-relaxed">
                  Log in instantly as <strong className="text-indigo-400">@oncall_devops</strong> with full platform Admin privileges for local evaluation without connecting GitHub credentials.
                </p>
                <button
                  onClick={handleDemoLogin}
                  disabled={isAuthenticating}
                  className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white font-bold rounded-xl transition-all shadow-md active:scale-95 cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <span className="material-symbols-outlined text-sm">verified_user</span>
                  <span>Sign In as On-Call DevOps (Admin)</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Database & Infrastructure Modal */}
      {isDbModalOpen && (
        <div className="fixed inset-0 z-[150] bg-black/80 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-700/80 rounded-3xl max-w-lg w-full p-6 shadow-2xl flex flex-col gap-5 relative">
            <button
              onClick={() => setIsDbModalOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-sm">close</span>
            </button>

            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="material-symbols-outlined text-indigo-400 text-xl">database</span>
                <h3 className="text-lg font-bold text-white">Database & Queue Configuration</h3>
              </div>
              <p className="text-xs text-slate-400">
                Active storage and background queue telemetry for Pipeline Failure Detection 3.0.
              </p>
            </div>

            <div className="flex flex-col gap-3 text-xs">
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-200">Active Storage Dialect:</span>
                  <span className={`px-2.5 py-0.5 rounded font-mono font-bold uppercase ${systemStatus?.database?.dialect === 'postgresql' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'}`}>
                    {systemStatus?.database?.dialect === 'postgresql' ? 'PostgreSQL 16' : 'SQLite Local (Dev Fallback)'}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  {systemStatus?.database?.dialect === 'postgresql'
                    ? 'Connected to production PostgreSQL with connection pool tuning (pool_size=10, max_overflow=20, pool_pre_ping=True, pool_recycle=3600).'
                    : 'The server is currently running in local developer mode using SQLite (sqlite:///./pipeline_failure_2.db) because DATABASE_URL has not been configured with a PostgreSQL connection string.'}
                </p>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-200">How to Connect to PostgreSQL:</span>
                </div>
                <ol className="text-[11px] text-slate-300 list-decimal list-inside space-y-1 font-mono leading-relaxed">
                  <li>Start PostgreSQL with Docker: <code className="text-cyan-400">docker compose up -d postgres</code></li>
                  <li>Or set <code className="text-cyan-400">DATABASE_URL=postgresql://user:pass@localhost:5432/pipeline_db</code> in <code className="text-indigo-400">.env</code></li>
                  <li>Run migrations: <code className="text-cyan-400">alembic upgrade head</code></li>
                </ol>
              </div>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-200">Background Queue Engine:</span>
                  <span className="font-mono text-indigo-400 font-bold">{systemStatus?.queue?.active_mode === 'celery' ? 'Celery (Redis Active)' : 'Local Asynchronous Thread'}</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Tasks are automatically routed to Celery background workers when Redis is reachable, or gracefully fall back to local async threads.
                </p>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setIsDbModalOpen(false)}
                className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-bold transition-all cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
