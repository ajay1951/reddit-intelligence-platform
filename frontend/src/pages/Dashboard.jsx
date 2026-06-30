import { useEffect, useState } from 'react';
import axios from 'axios';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, Database, MessageSquare, ExternalLink } from 'lucide-react';
import './Dashboard.css';

export default function Dashboard() {
  const [skills, setSkills] = useState([]);
  const [trends, setTrends] = useState([]);
  const [ingestion, setIngestion] = useState({ total_posts: 0, total_comments: 0, monitored_subreddits: 0 });
  const [recentPosts, setRecentPosts] = useState([]);
  const [subredditVolume, setSubredditVolume] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [skillsRes, trendsRes, ingestRes, recentRes, volRes] = await Promise.all([
          axios.get('http://localhost:8000/skills'),
          axios.get('http://localhost:8000/stats/trends_over_time'),
          axios.get('http://localhost:8000/stats/ingestion'),
          axios.get('http://localhost:8000/stats/recent_posts'),
          axios.get('http://localhost:8000/stats/subreddit_volume')
        ]);
        
        setSkills(skillsRes.data);
        setIngestion(ingestRes.data);
        setRecentPosts(recentRes.data);
        setSubredditVolume(volRes.data);
        
        if (trendsRes.data && Array.isArray(trendsRes.data)) {
          const formatted = trendsRes.data.map(t => ({
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
    };
    fetchData();
    
    // Poll for new data every 15 seconds
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="loader-ring"></div>
        <p>Initializing Command Center...</p>
      </div>
    );
  }

  const maxSkillCount = Math.max(...skills.map(s => s.count), 1);

  return (
    <div className="dashboard-container">
      <div className="dashboard-header animate-fade-in delay-100">
        <h1 className="page-title">Data <span className="gradient-text">Operations Center</span></h1>
        <p className="subtitle">Real-time ingestion monitoring and market intelligence.</p>
      </div>
      
      {/* KPI Row (Operations Focus) */}
      <div className="kpi-grid animate-fade-in delay-200">
        <div className="glass-card kpi-card">
          <div className="kpi-icon blue"><Database size={24} /></div>
          <div className="kpi-data">
            <span className="kpi-value">{ingestion.total_posts.toLocaleString()}</span>
            <span className="kpi-label">Posts Ingested</span>
          </div>
        </div>
        <div className="glass-card kpi-card">
          <div className="kpi-icon purple"><MessageSquare size={24} /></div>
          <div className="kpi-data">
            <span className="kpi-value">{ingestion.total_comments.toLocaleString()}</span>
            <span className="kpi-label">Comments Extracted</span>
          </div>
        </div>
        <div className="glass-card kpi-card">
          <div className="kpi-icon cyan"><Activity size={24} /></div>
          <div className="kpi-data">
            <span className="kpi-value">{ingestion.monitored_subreddits}</span>
            <span className="kpi-label">Active Subreddits</span>
          </div>
        </div>
      </div>

      {/* Primary Operations Grid */}
      <div className="ops-grid animate-fade-in delay-300">
        
        {/* Live Activity Feed */}
        <div className="glass-card feed-widget">
          <div className="widget-header">
            <h3>Live Ingestion Feed</h3>
            <span className="widget-badge pulse">Streaming</span>
          </div>
          <div className="feed-list">
            {recentPosts.map((post, i) => (
              <div key={i} className="feed-item">
                <div className="feed-meta">
                  <span className="feed-sub">r/{post.subreddit}</span>
                  <span className="feed-time">{new Date(post.created_at).toLocaleTimeString()}</span>
                </div>
                <div className="feed-title">{post.title}</div>
                {post.url && (
                  <a href={post.url} target="_blank" rel="noreferrer" className="feed-link">
                    <ExternalLink size={12} /> View Source
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Subreddit Volume Chart */}
        <div className="glass-card chart-widget">
          <div className="widget-header">
            <h3>Subreddit Data Volume</h3>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={subredditVolume} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis 
                  dataKey="subreddit" 
                  stroke="var(--text-secondary)" 
                  fontSize={11} 
                  tickLine={false} 
                  axisLine={false}
                  dy={10}
                />
                <YAxis 
                  stroke="var(--text-secondary)" 
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
                    border: '1px solid var(--border-light)', 
                    borderRadius: '12px',
                    color: '#fff'
                  }}
                  itemStyle={{ color: 'var(--accent-purple)', fontWeight: 'bold' }}
                />
                <Bar dataKey="count" fill="var(--accent-purple)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      <div className="section-divider animate-fade-in delay-400">
        <h2>Market Intelligence</h2>
        <div className="divider-line"></div>
      </div>

      {/* Secondary Analytics Grid */}
      <div className="bento-grid animate-fade-in delay-400">
        
        {/* Skills Widget */}
        <div className="glass-card bento-item skills-widget">
          <div className="widget-header">
            <h3>Top Requested Skills</h3>
          </div>
          <div className="skills-list">
            {skills.map((skill, i) => (
              <div key={i} className="skill-item">
                <div className="skill-info">
                  <span className="skill-rank">#{i + 1}</span>
                  <span className="skill-name">{skill.name}</span>
                  <span className="skill-count">{skill.count}</span>
                </div>
                <div className="skill-bar-bg">
                  <div 
                    className="skill-bar-fill" 
                    style={{ width: `${(skill.count / maxSkillCount) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Trends Chart */}
        <div className="glass-card bento-item chart-widget">
          <div className="widget-header">
            <h3>Discussion Trends</h3>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends} margin={{ top: 20, right: 20, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-cyan)" stopOpacity={0.5}/>
                    <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis 
                  dataKey="date" 
                  stroke="var(--text-secondary)" 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false} 
                  dy={10}
                />
                <YAxis 
                  stroke="var(--text-secondary)" 
                  fontSize={12} 
                  tickLine={false} 
                  axisLine={false} 
                  dx={-10}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'rgba(20, 22, 30, 0.9)', 
                    backdropFilter: 'blur(10px)',
                    border: '1px solid var(--border-light)', 
                    borderRadius: '12px',
                    color: '#fff'
                  }}
                  itemStyle={{ color: 'var(--accent-cyan)', fontWeight: 'bold' }}
                />
                <Area 
                  type="monotone" 
                  dataKey="count" 
                  stroke="var(--accent-cyan)" 
                  strokeWidth={3} 
                  fillOpacity={1} 
                  fill="url(#colorCount)" 
                  activeDot={{ r: 6, fill: '#fff', stroke: 'var(--accent-cyan)', strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
