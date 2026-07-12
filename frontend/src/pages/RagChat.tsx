import { useState, useRef, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Send, Bot, User, Search, ChevronDown, ChevronUp } from 'lucide-react';
import './RagChat.css';

export default function RagChat() {
  const [messages, setMessages] = useState([{
    role: 'assistant',
    content: 'Hello! I am connected to your Reddit Intelligence database. What would you like to know?',
    sources: null
  }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const res = await apiClient.post('/search/rag', {
        query: userMessage,
        top_k: 25
      });
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: res.data.answer,
        sources: res.data.sources 
      }]);
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error searching the database.' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h1 className="page-title">AI <span className="gradient-text">Research Assistant</span></h1>
        <p className="subtitle">Ask questions based on your scraped Reddit data.</p>
      </div>

      <div className="chat-box glass-card">
        <div className="messages-area">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message-wrapper ${msg.role}`}>
              <div className="message-avatar">
                {msg.role === 'assistant' ? <Bot size={20} /> : <User size={20} />}
              </div>
              <div className="message-content">
                <div className="message-bubble">
                  {msg.content}
                </div>
                {msg.sources && msg.sources.length > 0 && (
                  <SourcesList sources={msg.sources} />
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="message-wrapper assistant">
              <div className="message-avatar"><Bot size={20} /></div>
              <div className="message-content">
                <div className="message-bubble loading-dots">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form className="chat-input-area" onSubmit={handleSend}>
          <input
            type="text"
            className="input-glass"
            placeholder="Ask about Python libraries, hiring trends..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="btn-primary" disabled={loading || !input.trim()}>
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}

function SourcesList({ sources }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="sources-container">
      <button 
        className="sources-toggle" 
        onClick={() => setExpanded(!expanded)}
      >
        <Search size={14} />
        {sources.length} sources retrieved
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      
      {expanded && (
        <div className="sources-list">
          {sources.map((s, i) => (
            <a key={i} href={s.metadata?.url} target="_blank" rel="noreferrer" className="source-item">
              <span className="source-badge">{s.metadata?.type || 'source'}</span>
              <p className="source-text">{s.document}</p>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
