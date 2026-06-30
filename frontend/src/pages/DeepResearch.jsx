import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { BrainCircuit, Database, LineChart, Search, FileText, CheckCircle2, ShieldAlert } from 'lucide-react';
import './DeepResearch.css';

const AgentStep = ({ icon: Icon, title, status, message }) => {
  return (
    <div className={`agent-step ${status}`}>
      <div className="agent-icon-wrapper">
        <Icon className="agent-icon" size={24} />
      </div>
      <div className="agent-details">
        <h4 className="agent-title">{title}</h4>
        <p className="agent-message">{message}</p>
      </div>
      <div className="agent-status-indicator">
        {status === 'running' && <div className="spinner"></div>}
        {status === 'complete' && <CheckCircle2 className="complete-icon" size={20} />}
      </div>
    </div>
  );
};

export default function DeepResearch() {
  const [topic, setTopic] = useState('');
  const [isResearching, setIsResearching] = useState(false);
  const [steps, setSteps] = useState([]);
  const [finalReport, setFinalReport] = useState('');
  const [error, setError] = useState('');

  const handleResearch = async (e) => {
    e.preventDefault();
    if (!topic.trim()) return;

    setIsResearching(true);
    setSteps([]);
    setFinalReport('');
    setError('');

    try {
      // We use fetch with Server-Sent Events equivalent reading via body stream
      // Actually, SSE requires GET in standard EventSource. Since our backend uses POST,
      // we must read the stream manually via fetch.
      const response = await fetch('http://localhost:8000/api/v1/deep-research', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ topic }),
      });

      if (!response.ok) {
        throw new Error('Research request failed');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || ''; // Keep the incomplete chunk

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.substring(6);
            try {
              const data = JSON.parse(dataStr);
              handleAgentEvent(data);
            } catch (e) {
              console.error('Failed to parse SSE JSON:', e);
            }
          }
        }
      }
    } catch (err) {
      console.error(err);
      setError('An error occurred during research. Ensure the backend is running.');
    } finally {
      setIsResearching(false);
    }
  };

  const handleAgentEvent = (event) => {
    if (event.step === 'final') {
      setFinalReport(event.data);
      return;
    }
    
    setSteps(prev => {
      const existing = prev.findIndex(s => s.step === event.step);
      const newStep = { ...event };
      if (existing >= 0) {
        const next = [...prev];
        next[existing] = newStep;
        return next;
      }
      return [...prev, newStep];
    });
  };

  const getIconForStep = (stepName) => {
    switch(stepName) {
      case 'research': return Search;
      case 'trends': return Database;
      case 'sentiment': return LineChart;
      case 'report': return FileText;
      case 'verify': return ShieldAlert;
      default: return BrainCircuit;
    }
  };

  const getTitleForStep = (stepName) => {
    switch(stepName) {
      case 'research': return 'Research Agent';
      case 'trends': return 'Trend Analysis Agent';
      case 'sentiment': return 'Sentiment Agent';
      case 'report': return 'Synthesis Agent';
      case 'verify': return 'Verification Agent';
      default: return 'Agent';
    }
  };

  return (
    <div className="deep-research-container">
      <div className="deep-research-header">
        <h2>Deep Research Terminal</h2>
        <p>Deploy a swarm of autonomous AI agents to conduct Palantir-style intelligence gathering.</p>
      </div>

      <div className="deep-research-layout">
        <div className="deep-research-sidebar">
          <div className="terminal-panel">
            <form onSubmit={handleResearch} className="research-form">
              <label htmlFor="topic">Intelligence Target</label>
              <input
                id="topic"
                type="text"
                placeholder="e.g. Docker adoption in enterprise"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                disabled={isResearching}
              />
              <button type="submit" disabled={isResearching || !topic.trim()} className="deploy-btn">
                <BrainCircuit size={18} />
                {isResearching ? 'Agents Deployed...' : 'Deploy Agents'}
              </button>
            </form>

            {error && <div className="error-message">{error}</div>}

            {steps.length > 0 && (
              <div className="agent-timeline">
                <h3>Agent Network Status</h3>
                <div className="timeline-container">
                  {steps.map((s, i) => (
                    <AgentStep 
                      key={i}
                      icon={getIconForStep(s.step)}
                      title={getTitleForStep(s.step)}
                      status={s.status}
                      message={s.message}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="deep-research-main">
          {finalReport ? (
            <div className="report-panel">
              <div className="report-header">
                <h3>Intelligence Briefing: {topic}</h3>
              </div>
              <div className="report-content markdown-body">
                <ReactMarkdown>{finalReport}</ReactMarkdown>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <BrainCircuit size={64} className="empty-icon" />
              <h3>Awaiting Directive</h3>
              <p>Input a target topic to deploy the agent swarm.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
