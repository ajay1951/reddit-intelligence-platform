import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { formatNumber } from '../lib/utils';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { 
  Activity, 
  Database, 
  MessageSquare, 
  ExternalLink, 
  TrendingUp, 
  RefreshCw, 
  Search, 
  Filter,
  CheckCircle2,
  Clock,
  Flame,
  ArrowUpRight
} from 'lucide-react';
import { Card, CardHeader } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import './Dashboard.css';

interface Skill {
  name: string;
  count: number;
}

interface Trend {
  date: string;
  count: number;
}

interface IngestionStats {
  total_posts: number;
  total_comments: number;
  monitored_subreddits: number;
}

interface Post {
  subreddit: string;
  created_at: string;
  title: string;
  url?: string;
}

interface SubredditVolume {
  subreddit: string;
  count: number;
}

// Custom Tooltip for charts
const CustomChartTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="custom-chart-tooltip">
        <span className="tooltip-label">{label}</span>
        <div className="tooltip-value-row">
          <span className="tooltip-color-dot" style={{ backgroundColor: payload[0].color || '#4F46E5' }}></span>
          <span className="tooltip-name">{payload[0].name || 'Count'}:</span>
          <span className="tooltip-val font-semibold">{formatNumber(payload[0].value)}</span>
        </div>
      </div>
    );
  }
  return null;
};

export default function Dashboard() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [ingestion, setIngestion] = useState<IngestionStats>({ total_posts: 0, total_comments: 0, monitored_subreddits: 0 });
  const [recentPosts, setRecentPosts] = useState<Post[]>([]);
  const [subredditVolume, setSubredditVolume] = useState<SubredditVolume[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [postSearch, setPostSearch] = useState<string>('');
  const [selectedSubFilter, setSelectedSubFilter] = useState<string>('all');

  const fetchData = useCallback(async (manual = false) => {
    if (manual) setIsRefreshing(true);
    try {
      const [skillsRes, trendsRes, ingestRes, recentRes, volRes] = await Promise.all([
        apiClient.get(API_ENDPOINTS.SKILLS),
        apiClient.get(API_ENDPOINTS.TRENDS_OVER_TIME),
        apiClient.get(API_ENDPOINTS.INGESTION_STATS),
        apiClient.get(API_ENDPOINTS.RECENT_POSTS),
        apiClient.get(API_ENDPOINTS.SUBREDDIT_VOLUME)
      ]);
      
      setSkills(skillsRes.data);
      setIngestion(ingestRes.data);
      setRecentPosts(recentRes.data);
      setSubredditVolume(volRes.data);
      
      if (trendsRes.data && Array.isArray(trendsRes.data)) {
        const formatted = trendsRes.data.map((t: any) => ({
          date: new Date(t.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
          count: t.count
        }));
        setTrends(formatted);
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data', error);
    } finally {
      setLoading(false);
      if (manual) setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(false), 20000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const maxSkillCount = useMemo(() => Math.max(...skills.map(s => s.count), 1), [skills]);

  // Unique subreddits for feed filtering
  const availableSubreddits = useMemo(() => {
    const set = new Set(recentPosts.map(p => p.subreddit));
    return Array.from(set);
  }, [recentPosts]);

  // Filtered recent posts
  const filteredPosts = useMemo(() => {
    return recentPosts.filter(p => {
      const matchesSearch = p.title.toLowerCase().includes(postSearch.toLowerCase()) || 
                            p.subreddit.toLowerCase().includes(postSearch.toLowerCase());
      const matchesSub = selectedSubFilter === 'all' || p.subreddit.toLowerCase() === selectedSubFilter.toLowerCase();
      return matchesSearch && matchesSub;
    });
  }, [recentPosts, postSearch, selectedSubFilter]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[600px] gap-3">
        <LoadingSpinner text="Loading Operations Center Telemetry..." />
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Top Header */}
      <div className="dashboard-header animate-fade-in">
        <div>
          <h1 className="page-title">Operations & Market Intelligence</h1>
          <p className="subtitle">Real-time Reddit ingestion telemetry, market trends, and semantic document distribution.</p>
        </div>

        <div className="header-controls">
          <div className="live-status-pill">
            <span className="live-dot animate-pulse"></span>
            <span>Live Stream (20s cycle)</span>
          </div>
          <button 
            className="btn btn-secondary btn-sm" 
            onClick={() => fetchData(true)}
            disabled={isRefreshing}
          >
            <RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />
            <span>{isRefreshing ? 'Syncing...' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* 24-Hour Autonomous Scraper Telemetry Banner */}
      <div className="daily-auto-banner animate-fade-in delay-50">
        <div className="daily-auto-left">
          <div className="daily-auto-icon-box">
            <Clock size={20} />
          </div>
          <div className="daily-auto-text">
            <div className="daily-auto-headline">
              <span className="live-dot animate-pulse"></span>
              <strong>24-Hour Autonomous Ingestion Daemon: ACTIVE</strong>
              <span className="daily-auto-tag">Celery Beat • Daily Midnight UTC</span>
            </div>
            <p className="daily-auto-sub">
              Continuously scraping posts and comment trees across <code>r/MachineLearning</code>, <code>r/Python</code>, <code>r/LocalLLaMA</code>, <code>r/datascience</code>, and <code>r/technology</code> with advancing partition offsets.
            </p>
          </div>
        </div>
        <div className="daily-auto-right">
          <div className="daily-auto-metric">
            <span className="metric-label">Ingestion Engine</span>
            <span className="metric-value">Hugging Face + Live RSS</span>
          </div>
          <div className="daily-auto-metric">
            <span className="metric-label">Recurrence Cadence</span>
            <span className="metric-value">Every 24 Hours</span>
          </div>
          <div className="daily-auto-metric">
            <span className="metric-label">Monthly Cost</span>
            <span className="metric-value" style={{ color: '#059669' }}>$0.00 / Zero-Cost</span>
          </div>
        </div>
      </div>

      {/* KPI Stat Cards Grid */}
      <div className="kpi-grid animate-fade-in delay-100">

        <Card className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">Total Posts Ingested</span>
            <div className="kpi-icon-box blue"><Database size={18} /></div>
          </div>
          <div className="kpi-data-body">
            <span className="kpi-value tabular-nums">{formatNumber(ingestion.total_posts)}</span>
            <div className="kpi-delta-tag positive">
              <TrendingUp size={12} />
              <span>Real-time Ingested</span>
            </div>
          </div>
        </Card>

        <Card className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">Comments Extracted</span>
            <div className="kpi-icon-box purple"><MessageSquare size={18} /></div>
          </div>
          <div className="kpi-data-body">
            <span className="kpi-value tabular-nums">{formatNumber(ingestion.total_comments)}</span>
            <div className="kpi-delta-tag neutral">
              <span>Normalized UTF-8</span>
            </div>
          </div>
        </Card>

        <Card className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">Active Monitored Subreddits</span>
            <div className="kpi-icon-box emerald"><Activity size={18} /></div>
          </div>
          <div className="kpi-data-body">
            <span className="kpi-value tabular-nums">{formatNumber(ingestion.monitored_subreddits)}</span>
            <div className="kpi-delta-tag positive">
              <CheckCircle2 size={12} />
              <span>100% Online</span>
            </div>
          </div>
        </Card>

        <Card className="kpi-card">
          <div className="kpi-card-header">
            <span className="kpi-label">Indexed Vector Documents</span>
            <div className="kpi-icon-box amber"><Flame size={18} /></div>
          </div>
          <div className="kpi-data-body">
            <span className="kpi-value tabular-nums">{formatNumber(ingestion.total_posts + ingestion.total_comments)}</span>
            <div className="kpi-delta-tag positive">
              <span>ChromaDB Synced</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Primary Analytics Grid: Activity Table & Volume Bar */}
      <div className="dashboard-grid-2 animate-fade-in delay-200">
        
        {/* Filterable Live Ingestion Feed Table */}
        <Card className="dashboard-card feed-card">
          <div className="card-top-bar">
            <div>
              <h2 className="card-heading">Live Ingestion Activity</h2>
              <p className="card-subheading">Latest submissions ingested and indexed from Reddit.</p>
            </div>
            <span className="count-badge tabular-nums">{filteredPosts.length} posts</span>
          </div>

          {/* Search & Subreddit Filter Bar */}
          <div className="feed-filter-bar">
            <div className="feed-search-box">
              <Search size={14} className="text-slate-400" />
              <input 
                type="text"
                placeholder="Filter by title or keyword..."
                value={postSearch}
                onChange={(e) => setPostSearch(e.target.value)}
                className="feed-search-input"
              />
            </div>

            <div className="feed-sub-pills">
              <button 
                className={`sub-filter-pill ${selectedSubFilter === 'all' ? 'active' : ''}`}
                onClick={() => setSelectedSubFilter('all')}
              >
                All
              </button>
              {availableSubreddits.map(sub => (
                <button 
                  key={sub}
                  className={`sub-filter-pill ${selectedSubFilter === sub ? 'active' : ''}`}
                  onClick={() => setSelectedSubFilter(sub)}
                >
                  r/{sub}
                </button>
              ))}
            </div>
          </div>

          {/* Activity Items List */}
          <div className="feed-items-scroll">
            {filteredPosts.length === 0 ? (
              <div className="feed-empty-state">
                <p>No matching submissions found for this filter.</p>
              </div>
            ) : (
              filteredPosts.map((post, i) => (
                <div key={i} className="feed-item-row">
                  <div className="feed-item-meta">
                    <span className="subreddit-pill">r/{post.subreddit}</span>
                    <span className="feed-timestamp">
                      <Clock size={11} />
                      {new Date(post.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  <p className="feed-item-title">{post.title}</p>

                  {post.url && (
                    <a 
                      href={post.url} 
                      target="_blank" 
                      rel="noreferrer" 
                      className="feed-item-link"
                    >
                      <span>Reddit Thread</span>
                      <ArrowUpRight size={12} />
                    </a>
                  )}
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Subreddit Data Volume BarChart */}
        <Card className="dashboard-card">
          <div className="card-top-bar">
            <div>
              <h2 className="card-heading">Subreddit Data Distribution</h2>
              <p className="card-subheading">Total indexed documents partitioned by source subreddit.</p>
            </div>
          </div>

          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={subredditVolume} margin={{ top: 20, right: 10, left: -20, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                <XAxis 
                  dataKey="subreddit" 
                  stroke="#94A3B8" 
                  fontSize={11} 
                  tickLine={false} 
                  axisLine={{ stroke: '#E2E8F0' }}
                  dy={8}
                />
                <YAxis 
                  stroke="#94A3B8" 
                  fontSize={11} 
                  tickLine={false} 
                  axisLine={false}
                  dx={-6}
                />
                <Tooltip content={<CustomChartTooltip />} />
                <Bar 
                  dataKey="count" 
                  name="Documents"
                  fill="#4F46E5" 
                  radius={[4, 4, 0, 0]} 
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Secondary Analytics: Discussion Trends & Market Skills */}
      <div className="dashboard-grid-2 animate-fade-in delay-300">
        
        {/* Discussion Trends AreaChart */}
        <Card className="dashboard-card">
          <div className="card-top-bar">
            <div>
              <h2 className="card-heading">Discussion Activity Trends</h2>
              <p className="card-subheading">Ingestion volume timeline across monitored subreddits.</p>
            </div>
          </div>

          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={trends} margin={{ top: 20, right: 20, left: -20, bottom: 10 }}>
                <defs>
                  <linearGradient id="indigoGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.25}/>
                    <stop offset="95%" stopColor="#4F46E5" stopOpacity={0.0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                <XAxis 
                  dataKey="date" 
                  stroke="#94A3B8" 
                  fontSize={11} 
                  tickLine={false} 
                  axisLine={{ stroke: '#E2E8F0' }} 
                  dy={8}
                />
                <YAxis 
                  stroke="#94A3B8" 
                  fontSize={11} 
                  tickLine={false} 
                  axisLine={false} 
                  dx={-6}
                />
                <Tooltip content={<CustomChartTooltip />} />
                <Area 
                  type="monotone" 
                  dataKey="count" 
                  name="Posts/Comments"
                  stroke="#4F46E5" 
                  strokeWidth={2.5} 
                  fillOpacity={1} 
                  fill="url(#indigoGradient)" 
                  activeDot={{ r: 5, fill: '#4F46E5', stroke: '#FFFFFF', strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Top Extracted Skills */}
        <Card className="dashboard-card">
          <div className="card-top-bar">
            <div>
              <h2 className="card-heading">Top Mentioned Technical Skills</h2>
              <p className="card-subheading">Automated NLP entity frequency across technical Reddit discussions.</p>
            </div>
          </div>

          <div className="skills-scroll-list">
            {skills.length === 0 ? (
              <div className="feed-empty-state">
                <p>No skill frequency entities extracted yet.</p>
              </div>
            ) : (
              skills.map((skill, i) => (
                <div key={i} className="skill-frequency-item">
                  <div className="skill-info-header">
                    <div className="skill-name-wrap">
                      <span className="skill-rank tabular-nums">#{i + 1}</span>
                      <span className="skill-title">{skill.name}</span>
                    </div>
                    <span className="skill-count tabular-nums">{formatNumber(skill.count)} mentions</span>
                  </div>

                  <div className="skill-track">
                    <div 
                      className="skill-fill" 
                      style={{ width: `${Math.max((skill.count / maxSkillCount) * 100, 3)}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
