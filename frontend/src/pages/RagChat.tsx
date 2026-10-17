import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { apiClient } from '../api/client';
import { 
  Send, 
  Bot, 
  User, 
  Search, 
  ChevronDown, 
  ChevronUp, 
  Sparkles, 
  Copy, 
  Check, 
  RotateCcw, 
  ExternalLink, 
  MessageSquare,
  Compass
} from 'lucide-react';
import './RagChat.css';

interface SourceMetadata {
  id?: string;
  subreddit?: string;
  author?: string;
  score?: number;
  type?: string;
  url?: string;
  title?: string;
}

interface SourceItem {
  document: string;
  metadata?: SourceMetadata;
}

interface ChatMessage {
  id: string;
  role: 'assistant' | 'user';
  content: string;
  sources?: SourceItem[] | null;
  timestamp: string;
}

const PROMPT_SUGGESTIONS = [
  {
    category: 'Architecture',
    prompt: 'What are developers saying about FastAPI vs Go in production backend services?'
  },
  {
    category: 'AI & ML',
    prompt: 'Summarize the top recommendations for running local LLMs and quantized models.'
  },
  {
    category: 'DevOps',
    prompt: 'What are the most common Kubernetes deployment headaches discussed recently?'
  },
  {
    category: 'Hiring Trends',
    prompt: 'What is the prevailing sentiment regarding tech hiring and remote compensation?'
  }
];

export default function RagChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome-msg',
      role: 'assistant',
      content: 'Welcome to the **Reddit Intelligence Assistant**. I synthesize evidence across your ingested subreddits using hybrid dense-sparse retrieval and cross-encoder verification. Ask an analytical query below to begin.',
      sources: null,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  const handleSendPrompt = async (promptText: string) => {
    const textToSend = promptText.trim();
    if (!textToSend || loading) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const res = await apiClient.post('/search/rag', {
        query: textToSend,
        top_k: 25
      });

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: res.data.answer || 'No synthesis generated.',
        sources: res.data.sources || null,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: '⚠️ **Retrieval Error:** Unable to reach the knowledge base. Please check ChromaDB and FastAPI backend health.',
        sources: null,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendPrompt(input);
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleReset = () => {
    setMessages([
      {
        id: 'welcome-reset',
        role: 'assistant',
        content: 'Conversation reset. Ask any research question across your ingested Reddit database.',
        sources: null,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
  };

  return (
    <div className="chat-layout-container">
      {/* Top Header */}
      <div className="chat-top-header">
        <div className="header-meta">
          <div className="header-icon-pill">
            <Compass size={18} className="text-indigo-600" />
          </div>
          <div>
            <h1 className="page-title">RAG Research Assistant</h1>
            <p className="subtitle">Hybrid RRF retrieval & cross-encoder reranked Reddit intelligence.</p>
          </div>
        </div>

        <div className="header-actions">
          <button className="btn btn-secondary btn-sm" onClick={handleReset} title="Reset Conversation">
            <RotateCcw size={14} />
            <span>New Session</span>
          </button>
        </div>
      </div>

      {/* Main Chat Workspace */}
      <div className="chat-workspace-card">
        {/* Messages Stream */}
        <div className="messages-stream">
          {messages.map((msg) => (
            <div key={msg.id} className={`message-row ${msg.role}`}>
              <div className="message-avatar">
                {msg.role === 'assistant' ? (
                  <Bot size={16} />
                ) : (
                  <User size={16} />
                )}
              </div>

              <div className="message-body">
                <div className="message-header-meta">
                  <span className="author-name">
                    {msg.role === 'assistant' ? 'Intelligence Model' : 'You'}
                  </span>
                  <span className="timestamp">{msg.timestamp}</span>
                </div>

                <div className="message-bubble">
                  {msg.role === 'assistant' ? (
                    <div className="markdown-prose">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p className="user-text">{msg.content}</p>
                  )}

                  {msg.role === 'assistant' && msg.id !== 'welcome-msg' && msg.id !== 'welcome-reset' && (
                    <div className="message-actions-bar">
                      <button 
                        className="msg-action-btn"
                        onClick={() => handleCopy(msg.id, msg.content)}
                        title="Copy answer"
                      >
                        {copiedId === msg.id ? (
                          <>
                            <Check size={13} className="text-emerald-600" />
                            <span className="text-emerald-600">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy size={13} />
                            <span>Copy</span>
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </div>

                {/* Sources Section */}
                {msg.sources && msg.sources.length > 0 && (
                  <SourcesDrawer sources={msg.sources} />
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message-row assistant">
              <div className="message-avatar">
                <Bot size={16} />
              </div>
              <div className="message-body">
                <div className="message-bubble loading-shimmer">
                  <div className="loading-header">
                    <Sparkles size={14} className="text-indigo-600 animate-spin" />
                    <span>Executing hybrid retrieval & reranking sources...</span>
                  </div>
                  <div className="skeleton-line full"></div>
                  <div className="skeleton-line partial"></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggestion Deck (When conversation is fresh) */}
        {messages.length <= 1 && !loading && (
          <div className="suggestions-deck">
            <span className="suggestions-label">
              <Sparkles size={13} className="text-indigo-600" />
              <span>Recommended Inquiries</span>
            </span>
            <div className="suggestions-grid">
              {PROMPT_SUGGESTIONS.map((item, idx) => (
                <button 
                  key={idx}
                  className="suggestion-pill-card"
                  onClick={() => handleSendPrompt(item.prompt)}
                >
                  <span className="suggestion-category">{item.category}</span>
                  <span className="suggestion-text">{item.prompt}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Prompt Studio */}
        <div className="prompt-studio">
          <form 
            onSubmit={(e) => {
              e.preventDefault();
              handleSendPrompt(input);
            }} 
            className="prompt-form"
          >
            <div className="textarea-wrapper">
              <textarea
                ref={textareaRef}
                rows={1}
                className="prompt-textarea"
                placeholder="Ask an analytical question across indexed discussions... (Enter to send, Shift+Enter for new line)"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
              />
              <button 
                type="submit" 
                className="prompt-submit-btn" 
                disabled={loading || !input.trim()}
                title="Send query (Enter)"
              >
                <Send size={16} />
              </button>
            </div>
          </form>
          <div className="prompt-footer-hints">
            <span>Press <kbd>Enter ↵</kbd> to execute • <kbd>Shift + Enter</kbd> for line break</span>
            <span>25 Documents Retrieved • Top RRF Candidates Evaluated</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function SourcesDrawer({ sources }: { sources: SourceItem[] }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="sources-drawer">
      <button 
        type="button"
        className={`sources-toggle-btn ${expanded ? 'expanded' : ''}`}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="sources-toggle-left">
          <Search size={14} className="text-indigo-600" />
          <span className="font-medium">
            {sources.length} Grounded Reddit Sources Retrieved
          </span>
        </div>
        <div className="sources-toggle-right">
          <span className="toggle-label">{expanded ? 'Hide Evidence' : 'Inspect Evidence'}</span>
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </button>

      {expanded && (
        <div className="sources-grid">
          {sources.map((s, idx) => {
            const subreddit = s.metadata?.subreddit || 'reddit';
            const author = s.metadata?.author || 'anonymous';
            const score = s.metadata?.score ?? 0;
            const type = s.metadata?.type || 'comment';
            const url = s.metadata?.url;

            return (
              <div key={idx} className="source-citation-card">
                <div className="citation-header">
                  <div className="citation-tags">
                    <span className="sub-badge">r/{subreddit}</span>
                    <span className="type-badge">{type}</span>
                  </div>
                  <div className="citation-meta">
                    <span className="author-tag">u/{author}</span>
                    <span className="score-tag">▲ {score}</span>
                  </div>
                </div>

                <p className="citation-snippet">{s.document}</p>

                {url && (
                  <a 
                    href={url} 
                    target="_blank" 
                    rel="noreferrer" 
                    className="citation-link"
                  >
                    <span>View original discussion</span>
                    <ExternalLink size={12} />
                  </a>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
