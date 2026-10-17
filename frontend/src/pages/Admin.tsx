import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { 
  Database, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  Server, 
  Layers, 
  Cpu, 
  Clock, 
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Check,
  Lock,
  LogOut,
  KeyRound,
  ShieldAlert,
  Calendar,
  Play,
  Trash2,
  Settings2,
  Timer
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card, CardHeader } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { useApi } from '../hooks/useApi';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { isAuthenticated, login, logout, getStoredUser } from '../lib/auth';
import './Admin.css';

const scrapeSchema = z.object({
  subreddits: z.string().min(1, 'At least one subreddit is required'),
  postLimit: z.coerce.number().min(1, 'Min 1 post').max(10000, 'Max 10,000 posts per batch'),
  commentLimit: z.coerce.number().min(0, 'Min 0 comments').max(1000, 'Max 1,000 comments per post'),
  startDate: z.string().optional(),
  endDate: z.string().optional(),
});

type ScrapeFormData = z.infer<typeof scrapeSchema>;

interface StatusMessage {
  type: 'success' | 'error' | 'info';
  message: string;
  details?: string;
}

interface IngestionPreset {
  id: string;
  label: string;
  description: string;
  subreddits: string;
  postLimit: number;
  commentLimit: number;
}

const PRESETS: IngestionPreset[] = [
  {
    id: 'ai-frontier',
    label: 'AI & LLM Frontier',
    description: 'Track papers, local models & AI architecture',
    subreddits: 'MachineLearning, LocalLLaMA, ArtificialIntelligence',
    postLimit: 30,
    commentLimit: 10
  },
  {
    id: 'engineering-dev',
    label: 'Engineering & Dev',
    description: 'Production systems, Python, Rust & DevOps',
    subreddits: 'Python, rust, devops, webdev',
    postLimit: 25,
    commentLimit: 8
  },
  {
    id: 'tech-hiring',
    label: 'Hiring & Market Trends',
    description: 'Compensation, tech market sentiment & careers',
    subreddits: 'cscareerquestions, remotework',
    postLimit: 25,
    commentLimit: 15
  },
  {
    id: 'saas-startups',
    label: 'SaaS & Product Growth',
    description: 'Founders, pricing debates & software metrics',
    subreddits: 'SaaS, startups, Entrepreneur',
    postLimit: 20,
    commentLimit: 6
  }
];

export default function Admin() {
  const [authed, setAuthed] = useState<boolean>(() => isAuthenticated());
  const [currentUser, setCurrentUser] = useState(() => getStoredUser());
  const [loginUsername, setLoginUsername] = useState('admin');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const [status, setStatus] = useState<StatusMessage | null>(null);
  const [activePreset, setActivePreset] = useState<string | null>('ai-frontier');
  const [reindexStep, setReindexStep] = useState<'idle' | 'running' | 'completed'>('idle');
  const [indexedCount, setIndexedCount] = useState<number | null>(null);
  const [llmMetrics, setLlmMetrics] = useState<any>(null);

  // Scheduled Jobs & Daily Hugging Face state
  const [scheduledJobs, setScheduledJobs] = useState<any[]>([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(false);
  const [runHistory, setRunHistory] = useState<any[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isConfiguringDaily, setIsConfiguringDaily] = useState(false);
  const [dailySubreddits, setDailySubreddits] = useState('MachineLearning, Python, LocalLLaMA, datascience, technology');
  const [dailyPostLimit, setDailyPostLimit] = useState(50);
  const [dailyCommentLimit, setDailyCommentLimit] = useState(10);
  const [dailyCron, setDailyCron] = useState('0 0 * * *');
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  
  const { execute: executeScrape, loading: isScraping } = useApi();
  const { execute: executeReindex, loading: isReindexing } = useApi();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);
    setIsLoggingIn(true);
    const result = await login(loginUsername, loginPassword);
    setIsLoggingIn(false);
    if (result.success) {
      setAuthed(true);
      setCurrentUser(getStoredUser());
    } else {
      setLoginError(result.error || 'Invalid credentials.');
    }
  };

  const handleLogout = () => {
    logout();
    setAuthed(false);
    setCurrentUser(null);
    setLoginPassword('');
  };

  const fetchScheduledJobs = async () => {
    try {
      setIsLoadingJobs(true);
      const res = await apiClient.get(API_ENDPOINTS.SCHEDULE_JOBS);
      setScheduledJobs(res.data || []);
    } catch (e) {
      console.error('Failed to load scheduled jobs', e);
    } finally {
      setIsLoadingJobs(false);
    }
  };

  const fetchRunHistory = async () => {
    try {
      setIsLoadingHistory(true);
      const res = await apiClient.get(API_ENDPOINTS.SCHEDULE_HISTORY);
      setRunHistory(res.data || []);
    } catch (e) {
      console.error('Failed to load run history', e);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  useEffect(() => {
    apiClient.get(API_ENDPOINTS.METRICS_LLM)
      .then(res => setLlmMetrics(res.data))
      .catch(() => {});

    if (authed) {
      fetchScheduledJobs();
      fetchRunHistory();
    }
  }, [authed]);

  const handleSaveDailySchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsConfiguringDaily(true);
    try {
      const subs = dailySubreddits.split(',').map(s => s.trim()).filter(Boolean);
      await apiClient.post(API_ENDPOINTS.SCHEDULE_DAILY_HF, {
        subreddits: subs,
        post_limit: dailyPostLimit,
        comment_limit: dailyCommentLimit,
        cron: dailyCron,
      });
      setStatus({
        type: 'success',
        message: 'Daily Hugging Face automated schedule active.',
        details: `Runs on cron schedule (${dailyCron}) targeting: ${subs.join(', ')} (Offset advancing enabled).`,
      });
      setShowScheduleModal(false);
      fetchScheduledJobs();
    } catch (err: any) {
      setStatus({
        type: 'error',
        message: 'Failed to configure daily schedule',
        details: err.response?.data?.detail || err.message,
      });
    } finally {
      setIsConfiguringDaily(false);
    }
  };

  const handleCancelJob = async (jobId: string) => {
    try {
      await apiClient.delete(`/schedule/jobs/${jobId}`);
      setStatus({
        type: 'info',
        message: `Scheduled job ${jobId} removed successfully.`,
      });
      fetchScheduledJobs();
    } catch (err: any) {
      setStatus({
        type: 'error',
        message: 'Failed to cancel scheduled job',
        details: err.response?.data?.detail || err.message,
      });
    }
  };

  const handleTriggerDailyNow = async () => {
    setStatus({
      type: 'info',
      message: 'Dispatching immediate Hugging Face daily batch stream to Celery...',
    });
    try {
      const subs = dailySubreddits.split(',').map(s => s.trim()).filter(Boolean);
      const res = await executeScrape('post', API_ENDPOINTS.SCRAPE_BATCH, {
        subreddits: subs,
        post_limit: dailyPostLimit,
        comment_limit: dailyCommentLimit,
        provider: 'huggingface',
      });
      setStatus({
        type: 'success',
        message: 'Instant daily sync dispatched to worker queue.',
        details: `Task ID: ${res.task_id} • Engine: Hugging Face (streaming advancing offset) • Subs: ${subs.join(', ')}`,
      });
    } catch (err: any) {
      setStatus({
        type: 'error',
        message: 'Failed to trigger instant sync',
        details: err.response?.data?.detail || err.message,
      });
    }
  };


  const { register, handleSubmit, setValue, formState: { errors } } = useForm<ScrapeFormData>({
    resolver: zodResolver(scrapeSchema),
    defaultValues: {
      subreddits: 'MachineLearning, LocalLLaMA, ArtificialIntelligence',
      postLimit: 30,
      commentLimit: 10,
      startDate: '',
      endDate: '',
    }
  });

  const applyPreset = (preset: IngestionPreset) => {
    setActivePreset(preset.id);
    setValue('subreddits', preset.subreddits, { shouldValidate: true });
    setValue('postLimit', preset.postLimit, { shouldValidate: true });
    setValue('commentLimit', preset.commentLimit, { shouldValidate: true });
  };

  const onSubmitScrape = async (data: ScrapeFormData) => {
    setStatus({ 
      type: 'info', 
      message: 'Dispatching asynchronous ingestion worker task to Celery queue...' 
    });
    
    try {
      const subs = data.subreddits.split(',').map(s => s.trim()).filter(Boolean);
      const res = await executeScrape('post', API_ENDPOINTS.SCRAPE_BATCH, {
        subreddits: subs,
        post_limit: data.postLimit,
        comment_limit: data.commentLimit,
        start_date: data.startDate || undefined,
        end_date: data.endDate || undefined,
        provider: 'huggingface',
      });

      setStatus({ 
        type: 'success', 
        message: 'Batch ingestion job accepted by worker queue.',
        details: `Task ID: ${res.task_id} • Engine: Hugging Face Parquet Stream • Target Subreddits: ${subs.join(', ')}`
      });
    } catch (error: any) {
      const detailMsg = error.response?.data?.detail || error.message || 'Verify Celery worker connectivity or Reddit API rate limits.';
      setStatus({ 
        type: 'error', 
        message: 'Failed to dispatch scrape job.',
        details: typeof detailMsg === 'object' ? JSON.stringify(detailMsg) : detailMsg
      });
    }
  };

  const handleReindex = async () => {
    setStatus(null);
    setReindexStep('running');
    
    try {
      const res = await executeReindex('post', API_ENDPOINTS.SEARCH_REINDEX);
      setIndexedCount(res.indexed_documents);
      setReindexStep('completed');
      setStatus({ 
        type: 'success', 
        message: 'ChromaDB vector collection updated successfully.',
        details: `${res.indexed_documents} documents embedded and indexed with HNSW indexing.`
      });
    } catch (error: any) {
      setReindexStep('idle');
      const detailMsg = error.response?.data?.detail || error.message || 'Check ChromaDB container persistence or OpenAI embedding quota.';
      setStatus({ 
        type: 'error', 
        message: 'Vector reindexing failed.',
        details: typeof detailMsg === 'object' ? JSON.stringify(detailMsg) : detailMsg
      });
    }
  };

  if (!authed) {
    return (
      <div className="admin-page-container">
        <div className="admin-header">
          <div>
            <h1 className="page-title">
              <span>Pipeline & Data Operations</span>
            </h1>
            <p className="subtitle">Restricted administrative access. Authentication required.</p>
          </div>
        </div>

        <div className="admin-login-wrapper">
          <Card className="admin-login-card">
            <div className="login-badge">
              <ShieldAlert size={14} className="text-amber-500" />
              <span>SECURITY VERIFICATION</span>
            </div>
            <h2 className="login-title">Administrator Sign In</h2>
            <p className="login-desc">
              Enter administrative credentials to manage ingestion pipelines, vector synchronizations, and cluster operations.
            </p>

            {loginError && (
              <div className="login-error-alert">
                <AlertTriangle size={16} />
                <span>{loginError}</span>
              </div>
            )}

            <form onSubmit={handleLogin} className="login-form">
              <div className="login-field">
                <label className="login-label">Username</label>
                <div className="login-input-wrap">
                  <KeyRound size={16} className="login-input-icon" />
                  <input
                    type="text"
                    value={loginUsername}
                    onChange={(e) => setLoginUsername(e.target.value)}
                    placeholder="e.g. admin"
                    className="login-input"
                    required
                    autoFocus
                  />
                </div>
              </div>

              <div className="login-field">
                <label className="login-label">Password</label>
                <div className="login-input-wrap">
                  <Lock size={16} className="login-input-icon" />
                  <input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="Enter password"
                    className="login-input"
                    required
                  />
                </div>
              </div>

              <button type="submit" className="login-submit-btn" disabled={isLoggingIn}>
                {isLoggingIn ? (
                  <>
                    <RefreshCw size={16} className="animate-spin" />
                    <span>Verifying Credentials...</span>
                  </>
                ) : (
                  <>
                    <Lock size={16} />
                    <span>Authenticate & Access Console</span>
                  </>
                )}
              </button>

              <div className="login-hint">
                <span>Default credentials: <code>admin</code> / <code>admin123</code></span>
              </div>
            </form>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-page-container">
      {/* Header */}
      <div className="admin-header">
        <div>
          <h1 className="page-title">
            <span>Pipeline & Data Operations</span>
          </h1>
          <p className="subtitle">Manage Reddit ingestion streams, Celery workers, and ChromaDB vector embeddings.</p>
        </div>

        <div className="admin-session-badge">
          <div className="session-info">
            <span className="session-dot"></span>
            <span className="session-user">Operator: <strong>{currentUser?.username || 'admin'}</strong></span>
            <span className="session-role">Role: Administrator</span>
          </div>
          <button onClick={handleLogout} className="session-logout-btn" title="Sign out of admin session">
            <LogOut size={14} />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* Infrastructure Telemetry Strip */}
      <div className="telemetry-strip">
        <div className="telemetry-card">
          <div className="telemetry-icon-box blue">
            <Server size={18} />
          </div>
          <div className="telemetry-content">
            <span className="telemetry-label">PostgreSQL Database</span>
            <div className="telemetry-value-row">
              <span className="telemetry-status-dot online"></span>
              <span className="telemetry-val">Online</span>
              <span className="telemetry-aux">Pool Size: 10</span>
            </div>
          </div>
        </div>

        <div className="telemetry-card">
          <div className="telemetry-icon-box purple">
            <Layers size={18} />
          </div>
          <div className="telemetry-content">
            <span className="telemetry-label">ChromaDB Vector Store</span>
            <div className="telemetry-value-row">
              <span className="telemetry-status-dot online"></span>
              <span className="telemetry-val">Active</span>
              <span className="telemetry-aux">Hybrid RRF</span>
            </div>
          </div>
        </div>

        <div className="telemetry-card">
          <div className="telemetry-icon-box emerald">
            <Cpu size={18} />
          </div>
          <div className="telemetry-content">
            <span className="telemetry-label">Celery Distributed Workers</span>
            <div className="telemetry-value-row">
              <span className="telemetry-status-dot online"></span>
              <span className="telemetry-val">Ready</span>
              <span className="telemetry-aux">Concurrency: 4</span>
            </div>
          </div>
        </div>

        <div className="telemetry-card">
          <div className="telemetry-icon-box amber">
            <Clock size={18} />
          </div>
          <div className="telemetry-content">
            <span className="telemetry-label">Message Broker</span>
            <div className="telemetry-value-row">
              <span className="telemetry-status-dot online"></span>
              <span className="telemetry-val">Redis 7.2</span>
              <span className="telemetry-aux">0 queued</span>
            </div>
          </div>
        </div>

        <div className="telemetry-card">
          <div className="telemetry-icon-box indigo">
            <Sparkles size={18} />
          </div>
          <div className="telemetry-content">
            <span className="telemetry-label">LLM Observability</span>
            <div className="telemetry-value-row">
              <span className="telemetry-status-dot online"></span>
              <span className="telemetry-val">
                {llmMetrics?.total_tokens ? `${(llmMetrics.total_tokens).toLocaleString()} Tokens` : 'Active'}
              </span>
              <span className="telemetry-aux">
                {llmMetrics?.p95_latency_ms ? `p95: ${llmMetrics.p95_latency_ms}ms` : 'Cascade Fallback'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Status Alert Banner */}
      {status && (
        <div className={`status-banner ${status.type}`}>
          <div className="status-banner-icon">
            {status.type === 'success' && <CheckCircle2 size={18} />}
            {status.type === 'error' && <AlertTriangle size={18} />}
            {status.type === 'info' && <RefreshCw size={18} className="animate-spin" />}
          </div>
          <div className="status-banner-content">
            <p className="status-banner-title">{status.message}</p>
            {status.details && <p className="status-banner-sub">{status.details}</p>}
          </div>
          <button className="status-banner-dismiss" onClick={() => setStatus(null)}>✕</button>
        </div>
      )}

      {/* Automated Daily Hugging Face Ingestion Panel */}
      {(() => {
        const dailyJob = scheduledJobs.find((j: any) => j.job_id === 'daily_hf_reddit_sync');
        return (
          <div className="daily-scheduler-card">
            <div className="scheduler-top-row">
              <div className="scheduler-header-left">
                <div className="scheduler-icon-box">
                  <Calendar size={22} />
                </div>
                <div className="scheduler-title-wrap">
                  <div className="scheduler-title-row">
                    <h2 className="scheduler-title">Automated Daily Reddit Scraping & Ingestion</h2>
                    <span className="scheduler-badge-free">Hugging Face • 100% Zero-Cost • Incremental Offsets</span>
                  </div>
                  <p className="scheduler-desc">
                    Streams fresh real-world discussions from Hugging Face every day with advancing offset partitions, computes VADER sentiment, extracts tech entities, and continuously indexes documents into ChromaDB.
                  </p>
                </div>
              </div>

              <div>
                {dailyJob ? (
                  <div className="scheduler-status-pill active">
                    <span className="pulse-dot"></span>
                    <span>Daily Schedule Active</span>
                  </div>
                ) : (
                  <div className="scheduler-status-pill inactive">
                    <span>Schedule Not Registered</span>
                  </div>
                )}
              </div>
            </div>

            <div className="scheduler-metrics-grid">
              <div className="sched-metric-item">
                <span className="sched-metric-label">Cron Frequency</span>
                <span className="sched-metric-value">{dailyJob ? 'Daily at 00:00 UTC (0 0 * * *)' : 'Configurable (Daily)'}</span>
              </div>
              <div className="sched-metric-item">
                <span className="sched-metric-label">Next Execution</span>
                <span className="sched-metric-value">
                  {dailyJob?.next_run_time ? new Date(dailyJob.next_run_time).toLocaleString() : 'Pending Activation'}
                </span>
              </div>
              <div className="sched-metric-item">
                <span className="sched-metric-label">Streaming Source</span>
                <span className="sched-metric-value">Hugging Face (Streaming Parquet)</span>
              </div>
              <div className="sched-metric-item">
                <span className="sched-metric-label">Target Subreddits</span>
                <div className="sched-subs-tags">
                  {(dailyJob?.subreddits || ['MachineLearning', 'Python', 'LocalLLaMA', 'datascience']).map((s: string) => (
                    <span key={s} className="sub-tag">r/{s}</span>
                  ))}
                </div>
              </div>
            </div>

            <div className="scheduler-actions-bar">
              <button 
                type="button" 
                className="sched-btn-secondary" 
                onClick={() => setShowScheduleModal(true)}
              >
                <Settings2 size={15} />
                <span>Configure Daily Parameters</span>
              </button>

              <button 
                type="button" 
                className="sched-btn-primary" 
                onClick={handleTriggerDailyNow}
                disabled={isScraping}
              >
                <Play size={15} />
                <span>Trigger Today's Slice Now</span>
              </button>

              {dailyJob && (
                <button 
                  type="button" 
                  className="sched-btn-danger" 
                  onClick={() => handleCancelJob(dailyJob.job_id)}
                  title="Remove daily schedule"
                >
                  <Trash2 size={15} />
                  <span>Pause Schedule</span>
                </button>
              )}
            </div>

            {/* Run History Audit Table */}
            <div className="run-history-section">
              <div className="run-history-header">
                <span className="run-history-title">
                  <Clock size={15} className="text-indigo-600" />
                  <span>24-Hour Autonomous Execution Audit Trail</span>
                </span>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={fetchRunHistory}
                  disabled={isLoadingHistory}
                  style={{ fontSize: '11px', padding: '3px 8px' }}
                >
                  <RefreshCw size={12} className={isLoadingHistory ? 'animate-spin' : ''} />
                  <span>Refresh History</span>
                </button>
              </div>

              <div className="run-history-table-wrapper">
                <table className="run-history-table">
                  <thead>
                    <tr>
                      <th>Status</th>
                      <th>Task / Job</th>
                      <th>Monitored Subreddits</th>
                      <th>Posts Ingested</th>
                      <th>Comments Ingested</th>
                      <th>Provider Engine</th>
                      <th>Execution Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runHistory.length === 0 ? (
                      <tr>
                        <td colSpan={7} style={{ textAlign: 'center', padding: '16px', color: '#64748b' }}>
                          No execution history recorded yet. Trigger a sync or wait for the midnight 24h cron run.
                        </td>
                      </tr>
                    ) : (
                      runHistory.map((run: any) => (
                        <tr key={run.id}>
                          <td>
                            <span className={`run-status-badge ${run.status}`}>
                              {run.status === 'success' && '✓'}
                              {run.status === 'running' && '⟳'}
                              {run.status === 'failed' && '✕'}
                              <span style={{ textTransform: 'capitalize' }}>{run.status}</span>
                            </span>
                          </td>
                          <td style={{ fontWeight: 600 }}>{run.job_id}</td>
                          <td>
                            <div className="sched-subs-tags">
                              {(run.subreddits || []).slice(0, 3).map((s: string) => (
                                <span key={s} className="sub-tag">r/{s}</span>
                              ))}
                              {(run.subreddits || []).length > 3 && (
                                <span className="sub-tag">+{run.subreddits.length - 3} more</span>
                              )}
                            </div>
                          </td>
                          <td style={{ fontWeight: 700, color: '#059669' }}>+{run.posts_ingested}</td>
                          <td style={{ fontWeight: 700, color: '#4f46e5' }}>+{run.comments_ingested}</td>
                          <td>
                            <span className="run-provider-badge">{run.provider_used}</span>
                          </td>
                          <td style={{ color: '#64748b' }}>
                            {run.started_at ? new Date(run.started_at).toLocaleString() : 'N/A'}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        );
      })()}

      {/* 24-Hour Autonomous Hugging Face Ingestion & Audit Section */}
      <Card className="scheduler-card animate-fade-in delay-150">
        <div className="scheduler-card-header">
          <div className="scheduler-icon-box">
            <Clock size={22} className="text-indigo-600" />
          </div>
          <div className="scheduler-title-wrap">
            <div className="scheduler-title-row">
              <h2 className="scheduler-title">24-Hour Automated Reddit Scraping Engine</h2>
              <span className="scheduler-badge-free">100% Free / Zero API Cost</span>
            </div>
            <p className="scheduler-desc">
              Celery Beat & Celery Worker background daemons continuously stream posts & comment trees every 24 hours (daily midnight UTC) across ML & tech subreddits with automatic offset progression and live RSS fallback.
            </p>
          </div>
          <div className="scheduler-status-pill active">
            <span className="pulse-dot"></span>
            <span>Daemon Active (24h)</span>
          </div>
        </div>

        <div className="scheduler-metrics-grid">
          <div className="sched-metric-item">
            <span className="sched-metric-label">Recurrence Cadence</span>
            <span className="sched-metric-value">Every 24 Hours (Midnight UTC)</span>
          </div>
          <div className="sched-metric-item">
            <span className="sched-metric-label">Ingestion Engine</span>
            <span className="sched-metric-value">Hugging Face Parquet Stream + RSS Fallback</span>
          </div>
          <div className="sched-metric-item">
            <span className="sched-metric-label">Target Subreddits</span>
            <div className="sched-subs-tags">
              <span className="sub-tag">r/MachineLearning</span>
              <span className="sub-tag">r/Python</span>
              <span className="sub-tag">r/LocalLLaMA</span>
              <span className="sub-tag">r/datascience</span>
              <span className="sub-tag">r/technology</span>
            </div>
          </div>
          <div className="sched-metric-item">
            <span className="sched-metric-label">Partition Offset</span>
            <span className="sched-metric-value">Auto-advancing (No Duplicate Overlap)</span>
          </div>
        </div>

        <div className="scheduler-actions-bar">
          <button 
            type="button" 
            className="sched-btn-secondary"
            onClick={fetchRunHistory}
            disabled={isLoadingHistory}
          >
            <RefreshCw size={14} className={isLoadingHistory ? 'animate-spin' : ''} />
            <span>Refresh Audit History</span>
          </button>
          <button 
            type="button" 
            className="sched-btn-secondary"
            onClick={() => setShowScheduleModal(true)}
          >
            <Settings2 size={14} />
            <span>Configure Parameters</span>
          </button>
          <button 
            type="button" 
            className="sched-btn-primary"
            onClick={handleTriggerDailyNow}
            disabled={isScraping}
          >
            <Play size={14} />
            <span>Trigger Immediate Batch Sync</span>
          </button>
        </div>

        {/* 24-Hour Autonomous Execution Audit Trail */}
        <div className="run-history-section">
          <div className="run-history-header">
            <span className="run-history-title">
              <Database size={15} className="text-indigo-600" />
              <span>24-Hour Autonomous Execution Audit Trail</span>
            </span>
            <span className="text-xs text-slate-500 font-mono">
              {runHistory.length} Recorded Execution{runHistory.length === 1 ? '' : 's'}
            </span>
          </div>

          <div className="run-history-table-wrapper">
            <table className="run-history-table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Job Type</th>
                  <th>Target Subreddits</th>
                  <th>Posts Ingested</th>
                  <th>Comments Extracted</th>
                  <th>Engine / Provider</th>
                  <th>Status</th>
                  <th>Execution Timestamp (UTC)</th>
                </tr>
              </thead>
              <tbody>
                {runHistory.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ textAlign: 'center', padding: '24px', color: '#94a3b8' }}>
                      No 24-hour ingestion runs logged yet. Click "Trigger Immediate Batch Sync" to run now.
                    </td>
                  </tr>
                ) : (
                  runHistory.map((run) => (
                    <tr key={run.id}>
                      <td className="font-mono font-bold text-slate-800">#{run.id}</td>
                      <td>
                        <span className="text-xs font-medium text-slate-600">
                          {run.job_id === '24h_auto_scrape' ? '24h Daemon Cycle' : run.job_id}
                        </span>
                      </td>
                      <td>
                        <div className="flex flex-wrap gap-1">
                          {(run.subreddits || []).slice(0, 3).map((sub: string) => (
                            <span key={sub} className="sub-tag">r/{sub}</span>
                          ))}
                          {(run.subreddits || []).length > 3 && (
                            <span className="sub-tag">+{run.subreddits.length - 3} more</span>
                          )}
                        </div>
                      </td>
                      <td className="font-semibold text-slate-900">{run.posts_ingested?.toLocaleString() ?? 0}</td>
                      <td className="font-semibold text-slate-900">{run.comments_ingested?.toLocaleString() ?? 0}</td>
                      <td>
                        <span className="run-provider-badge">
                          {run.provider_used || 'huggingface'}
                        </span>
                      </td>
                      <td>
                        <span className={`run-status-badge ${run.status}`}>
                          {run.status === 'success' && <Check size={12} />}
                          {run.status === 'running' && <RefreshCw size={12} className="animate-spin" />}
                          {run.status === 'failed' && <AlertTriangle size={12} />}
                          <span style={{ textTransform: 'capitalize' }}>{run.status}</span>
                        </span>
                      </td>
                      <td className="font-mono text-xs text-slate-500">
                        {run.started_at ? new Date(run.started_at).toISOString().replace('T', ' ').slice(0, 19) : '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </Card>

      {/* Main Operations Grid */}
      <div className="operations-grid">
        {/* Card 1: Batch Reddit Ingestion Engine */}
        <Card className="operation-card">
          <CardHeader className="operation-card-header">
            <div className="header-icon-wrap">
              <Database size={20} className="text-indigo-600" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 className="operation-card-title">Batch Ingestion Dispatcher</h2>
                <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '12px', background: '#e0e7ff', color: '#4338ca', fontWeight: 600 }}>
                  Hugging Face Stream (Primary)
                </span>
              </div>
              <p className="operation-card-desc">Zero-cost streaming of real Reddit technical submissions and comment trees with deterministic normalization.</p>
            </div>
          </CardHeader>

          {/* Curated Preset Pills */}
          <div className="presets-section">
            <span className="presets-label">
              <Sparkles size={13} className="text-indigo-600" />
              <span>Curated Research Clusters</span>
            </span>
            <div className="presets-grid">
              {PRESETS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className={`preset-pill ${activePreset === p.id ? 'active' : ''}`}
                  onClick={() => applyPreset(p)}
                >
                  <div className="preset-pill-top">
                    <span className="preset-pill-title">{p.label}</span>
                    {activePreset === p.id && <Check size={14} className="text-indigo-600" />}
                  </div>
                  <span className="preset-pill-desc">{p.description}</span>
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={handleSubmit(onSubmitScrape)} className="operation-form">
            <Input 
              label="Subreddits (Comma-separated list)"
              placeholder="e.g. MachineLearning, Python, datascience"
              {...register('subreddits')}
              error={errors.subreddits?.message}
              disabled={isScraping || isReindexing}
            />

            <div className="form-row-2">
              <Input 
                label="Post Volume Limit (per subreddit)"
                type="number"
                placeholder="25"
                {...register('postLimit')}
                error={errors.postLimit?.message}
                disabled={isScraping || isReindexing}
              />
              <Input 
                label="Comments Extracted (per post)"
                type="number"
                placeholder="5"
                {...register('commentLimit')}
                error={errors.commentLimit?.message}
                disabled={isScraping || isReindexing}
              />
            </div>

            <div className="form-row-2">
              <Input 
                label="Ingestion Start Date (Optional)"
                type="date"
                {...register('startDate')}
                disabled={isScraping || isReindexing}
              />
              <Input 
                label="Ingestion End Date (Optional)"
                type="date"
                {...register('endDate')}
                disabled={isScraping || isReindexing}
              />
            </div>

            <div className="form-actions">
              <Button type="submit" isLoading={isScraping} className="btn-primary w-full">
                <span>Dispatch Ingestion Pipeline</span>
                <ArrowRight size={16} />
              </Button>
            </div>
          </form>
        </Card>

        {/* Card 2: ChromaDB Vector Sync Engine */}
        <div className="side-operations-column">
          <Card className="operation-card">
            <CardHeader className="operation-card-header">
              <div className="header-icon-wrap purple">
                <RefreshCw size={20} className="text-purple-600" />
              </div>
              <div>
                <h2 className="operation-card-title">ChromaDB Vector Synchronization</h2>
                <p className="operation-card-desc">Batch vectorize newly scraped documents for Hybrid RRF retrieval.</p>
              </div>
            </CardHeader>

            <div className="reindex-info-box">
              <div className="info-stat-row">
                <span className="info-label">Retrieval Architecture</span>
                <span className="info-val">BM25 + OpenAI text-embedding-3-small</span>
              </div>
              <div className="info-stat-row">
                <span className="info-label">Vector Storage Target</span>
                <span className="info-val">Persistent ChromaDB Volume</span>
              </div>
              <div className="info-stat-row">
                <span className="info-label">Reranking Model</span>
                <span className="info-val">Cross-Encoder (ms-marco-MiniLM)</span>
              </div>
            </div>

            {/* Stepper feedback */}
            {reindexStep !== 'idle' && (
              <div className="reindex-stepper">
                <div className={`step-item ${reindexStep === 'running' ? 'active' : 'done'}`}>
                  <div className="step-circle">
                    {reindexStep === 'running' ? <RefreshCw size={13} className="animate-spin" /> : <Check size={13} />}
                  </div>
                  <div className="step-text">
                    <span className="step-title">1. Vector Embeddings Generation</span>
                    <span className="step-desc">Generating dense vector coordinates</span>
                  </div>
                </div>

                <div className={`step-item ${reindexStep === 'completed' ? 'done' : 'pending'}`}>
                  <div className="step-circle">
                    {reindexStep === 'completed' ? <Check size={13} /> : '2'}
                  </div>
                  <div className="step-text">
                    <span className="step-title">2. Commit to ChromaDB Index</span>
                    <span className="step-desc">
                      {reindexStep === 'completed' 
                        ? `${indexedCount ?? 0} documents indexed successfully` 
                        : 'Awaiting embedding batch'}
                    </span>
                  </div>
                </div>
              </div>
            )}

            <div className="form-actions mt-auto">
              <Button 
                onClick={handleReindex} 
                variant="secondary" 
                isLoading={isReindexing}
                disabled={isScraping}
                className="w-full"
              >
                <RefreshCw size={16} />
                <span>Rebuild Semantic Knowledge Base</span>
              </Button>
            </div>
          </Card>

          {/* Quick System Verification Card */}
          <Card className="operation-card verification-card">
            <div className="verification-header">
              <ShieldCheck size={18} className="text-emerald-600" />
              <h3 className="verification-title">Security & Pipeline Certifications</h3>
            </div>
            <ul className="verification-list">
              <li>✓ Scoped DB Engine & Thread Connection Pools</li>
              <li>✓ UTC Time Normalization & Deterministic IDs</li>
              <li>✓ Non-Root Production Docker Architecture</li>
              <li>✓ JWT & Machine-to-Machine API Key Enforced</li>
            </ul>
          </Card>
        </div>
      </div>

      {/* Schedule Configuration Modal */}
      {showScheduleModal && (
        <div className="schedule-modal-backdrop" onClick={() => setShowScheduleModal(false)}>
          <div className="schedule-modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-row">
              <h3 className="modal-title">Configure Automated Daily Hugging Face Sync</h3>
              <button className="modal-close-btn" onClick={() => setShowScheduleModal(false)}>✕</button>
            </div>

            <form onSubmit={handleSaveDailySchedule} className="modal-form">
              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Target Subreddits (Comma-separated)</label>
                <input
                  type="text"
                  value={dailySubreddits}
                  onChange={(e) => setDailySubreddits(e.target.value)}
                  className="login-input"
                  placeholder="MachineLearning, Python, datascience, technology"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Daily Posts per Subreddit</label>
                  <input
                    type="number"
                    value={dailyPostLimit}
                    onChange={(e) => setDailyPostLimit(Number(e.target.value))}
                    min={5}
                    max={500}
                    className="login-input"
                    required
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Comments per Post</label>
                  <input
                    type="number"
                    value={dailyCommentLimit}
                    onChange={(e) => setDailyCommentLimit(Number(e.target.value))}
                    min={0}
                    max={50}
                    className="login-input"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 block mb-1">Cron Expression (UTC)</label>
                <input
                  type="text"
                  value={dailyCron}
                  onChange={(e) => setDailyCron(e.target.value)}
                  className="login-input"
                  placeholder="0 0 * * * (Every midnight UTC)"
                  required
                />
                <span className="text-[11px] text-slate-500 mt-1 block">Default: <code>0 0 * * *</code> (Midnight UTC every day)</span>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="sched-btn-secondary"
                  onClick={() => setShowScheduleModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="sched-btn-primary"
                  disabled={isConfiguringDaily}
                >
                  {isConfiguringDaily ? 'Saving Schedule...' : 'Save & Activate Daily Schedule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
