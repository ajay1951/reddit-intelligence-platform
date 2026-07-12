import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { formatNumber } from '../lib/utils';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, Database, MessageSquare, ExternalLink } from 'lucide-react';
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

export default function Dashboard() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [ingestion, setIngestion] = useState<IngestionStats>({ total_posts: 0, total_comments: 0, monitored_subreddits: 0 });
  const [recentPosts, setRecentPosts] = useState<Post[]>([]);
  const [subredditVolume, setSubredditVolume] = useState<SubredditVolume[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchData = useCallback(async () => {
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
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const maxSkillCount = useMemo(() => Math.max(...skills.map(s => s.count), 1), [skills]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[600px]">
        <LoadingSpinner text="Initializing Command Center..." />
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-header animate-fade-in delay-100">
        <h1 className="page-title">Data <span className="gradient-text">Operations Center</span></h1>
        <p className="subtitle">Real-time ingestion monitoring and market intelligence.</p>
      </div>
      
      {/* KPI Row (Operations Focus) */}
      <div className="kpi-grid animate-fade-in delay-200">
        <Card className="kpi-card p-4 flex flex-row items-center gap-4">
          <div className="kpi-icon blue"><Database size={24} /></div>
          <div className="kpi-data flex flex-col">
            <span className="kpi-value font-bold text-2xl text-[var(--text-primary)]">{formatNumber(ingestion.total_posts)}</span>
            <span className="kpi-label text-sm text-[var(--text-secondary)]">Posts Ingested</span>
          </div>
        </Card>
        <Card className="kpi-card p-4 flex flex-row items-center gap-4">
          <div className="kpi-icon purple"><MessageSquare size={24} /></div>
          <div className="kpi-data flex flex-col">
            <span className="kpi-value font-bold text-2xl text-[var(--text-primary)]">{formatNumber(ingestion.total_comments)}</span>
            <span className="kpi-label text-sm text-[var(--text-secondary)]">Comments Extracted</span>
          </div>
        </Card>
        <Card className="kpi-card p-4 flex flex-row items-center gap-4">
          <div className="kpi-icon cyan"><Activity size={24} /></div>
          <div className="kpi-data flex flex-col">
            <span className="kpi-value font-bold text-2xl text-[var(--text-primary)]">{formatNumber(ingestion.monitored_subreddits)}</span>
            <span className="kpi-label text-sm text-[var(--text-secondary)]">Active Subreddits</span>
          </div>
        </Card>
      </div>

      {/* Primary Operations Grid */}
      <div className="ops-grid animate-fade-in delay-300 grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        
        {/* Live Activity Feed */}
        <Card className="feed-widget p-6">
          <CardHeader className="flex justify-between items-center mb-4">
            <h3 className="text-xl font-semibold">Live Ingestion Feed</h3>
            <span className="px-2 py-1 text-xs font-bold text-green-400 bg-green-400/10 rounded-full animate-pulse">Streaming</span>
          </CardHeader>
          <div className="feed-list flex flex-col gap-4 overflow-y-auto max-h-[300px]">
            {recentPosts.map((post, i) => (
              <div key={i} className="feed-item bg-white/50 p-3 rounded-lg border border-[var(--border-light)]">
                <div className="feed-meta flex justify-between text-xs text-[var(--text-secondary)] mb-1">
                  <span className="feed-sub font-semibold text-blue-400">r/{post.subreddit}</span>
                  <span className="feed-time">{new Date(post.created_at).toLocaleTimeString()}</span>
                </div>
                <div className="feed-title text-sm text-[var(--text-primary)]">{post.title}</div>
                {post.url && (
                  <a href={post.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 mt-2">
                    <ExternalLink size={12} /> View Source
                  </a>
                )}
              </div>
            ))}
          </div>
        </Card>

        {/* Subreddit Volume Chart */}
        <Card className="chart-widget p-6">
          <CardHeader className="mb-4">
            <h3 className="text-xl font-semibold">Subreddit Data Volume</h3>
          </CardHeader>
          <div className="chart-container h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={subredditVolume} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis 
                  dataKey="subreddit" 
                  stroke="#9ca3af" 
                  fontSize={11} 
                  tickLine={false} 
                  axisLine={false}
                  dy={10}
                />
                <YAxis 
                  stroke="#9ca3af" 
                  fontSize={11} 
                  tickLine={false} 
                  axisLine={false}
                  dx={-10}
                />
                <Tooltip 
                  cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }}
                  contentStyle={{ 
                    backgroundColor: 'rgba(20, 22, 30, 0.9)', 
                    backdropFilter: 'blur(10px)',
                    border: '1px solid #374151', 
                    borderRadius: '12px',
                    color: '#fff'
                  }}
                  itemStyle={{ color: '#a855f7', fontWeight: 'bold' }}
                />
                <Bar dataKey="count" fill="#a855f7" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="section-divider animate-fade-in delay-400 mt-12 mb-6 text-center relative">
        <h2 className="text-2xl font-bold bg-[#0b0c10] px-4 relative z-10 inline-block">Market Intelligence</h2>
        <div className="absolute top-1/2 left-0 w-full h-[1px] bg-gray-800 -z-0"></div>
      </div>

      {/* Secondary Analytics Grid */}
      <div className="bento-grid animate-fade-in delay-400 grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Skills Widget */}
        <Card className="bento-item skills-widget p-6">
          <CardHeader className="mb-4">
            <h3 className="text-xl font-semibold">Top Requested Skills</h3>
          </CardHeader>
          <div className="skills-list flex flex-col gap-3">
            {skills.map((skill, i) => (
              <div key={i} className="skill-item relative flex flex-col">
                <div className="skill-info flex justify-between text-sm z-10 mb-1">
                  <div className="flex gap-2">
                    <span className="skill-rank text-[var(--text-secondary)] font-mono">#{i + 1}</span>
                    <span className="skill-name text-[var(--text-primary)]">{skill.name}</span>
                  </div>
                  <span className="skill-count text-[var(--text-secondary)] font-mono">{formatNumber(skill.count)}</span>
                </div>
                <div className="skill-bar-bg w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div 
                    className="skill-bar-fill h-full bg-blue-500 rounded-full" 
                    style={{ width: `${(skill.count / maxSkillCount) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Trends Chart */}
        <Card className="bento-item chart-widget p-6">
          <CardHeader className="mb-4">
            <h3 className="text-xl font-semibold">Discussion Trends</h3>
          </CardHeader>
          <div className="chart-container h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends} margin={{ top: 20, right: 20, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.5}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis 
                  dataKey="date" 
                  stroke="#9ca3af" 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false} 
                  dy={10}
                />
                <YAxis 
                  stroke="#9ca3af" 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false} 
                  dx={-10}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'rgba(255, 255, 255, 0.8)', 
                    backdropFilter: 'blur(10px)',
                    border: '1px solid rgba(0, 0, 0, 0.1)', 
                    borderRadius: '12px',
                    color: '#1E293B'
                  }}
                  itemStyle={{ color: '#06b6d4', fontWeight: 'bold' }}
                />
                <Area 
                  type="monotone" 
                  dataKey="count" 
                  stroke="#06b6d4" 
                  strokeWidth={3} 
                  fillOpacity={1} 
                  fill="url(#colorCount)" 
                  activeDot={{ r: 6, fill: '#fff', stroke: '#06b6d4', strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  );
}
