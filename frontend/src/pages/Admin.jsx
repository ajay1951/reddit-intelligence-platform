import { useState } from 'react';
import axios from 'axios';
import { Database, RefreshCw, AlertCircle } from 'lucide-react';
import './Admin.css';

export default function Admin() {
  const [subreddits, setSubreddits] = useState('MachineLearning, Python, datascience');
  const [postLimit, setPostLimit] = useState(25);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleScrape = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus({ type: 'info', message: 'Scraping in progress... this may take a moment.' });
    
    try {
      const subs = subreddits.split(',').map(s => s.trim());
      const res = await axios.post('http://localhost:8000/scrape/batch', {
        subreddits: subs,
        post_limit: Number(postLimit),
        comment_limit: 5
      });
      setStatus({ 
        type: 'success', 
        message: `Scrape complete! Found ${res.data.total_posts_inserted} new posts and ${res.data.total_comments_inserted} new comments.` 
      });
    } catch (error) {
      setStatus({ type: 'error', message: 'Failed to run batch scrape.' });
    } finally {
      setLoading(false);
    }
  };

  const handleReindex = async () => {
    setLoading(true);
    setStatus({ type: 'info', message: 'Reindexing vectors... this uses the embedding API.' });
    
    try {
      const res = await axios.post('http://localhost:8000/search/reindex');
      setStatus({ 
        type: 'success', 
        message: `Reindex complete! ${res.data.indexed_documents} documents indexed.` 
      });
    } catch (error) {
      setStatus({ type: 'error', message: 'Failed to reindex documents.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="admin-container">
      <h1 className="page-title">System <span className="gradient-text">Administration</span></h1>
      
      {status && (
        <div className={`status-alert ${status.type}`}>
          <AlertCircle size={20} />
          {status.message}
        </div>
      )}

      <div className="admin-grid">
        <div className="glass-card admin-card">
          <div className="card-header">
            <Database className="card-icon" />
            <h3>Batch Scraper</h3>
          </div>
          <p className="card-desc">Trigger a massive data extraction from Reddit subreddits.</p>
          
          <form onSubmit={handleScrape} className="admin-form">
            <div className="form-group">
              <label>Subreddits (comma separated)</label>
              <input 
                type="text" 
                className="input-glass" 
                value={subreddits}
                onChange={(e) => setSubreddits(e.target.value)}
                disabled={loading}
              />
            </div>
            <div className="form-group">
              <label>Post Limit per Subreddit</label>
              <input 
                type="number" 
                className="input-glass" 
                value={postLimit}
                onChange={(e) => setPostLimit(e.target.value)}
                min="1" max="10000"
                disabled={loading}
              />
            </div>
            <button type="submit" className="btn-primary" disabled={loading}>
              Run Batch Scrape
            </button>
          </form>
        </div>

        <div className="glass-card admin-card">
          <div className="card-header">
            <RefreshCw className="card-icon" />
            <h3>Vector Reindex</h3>
          </div>
          <p className="card-desc">Generate embeddings for all new posts and comments to update the RAG AI's knowledge base.</p>
          
          <div className="admin-form">
            <button onClick={handleReindex} className="btn-primary" disabled={loading}>
              Trigger Full Reindex
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
