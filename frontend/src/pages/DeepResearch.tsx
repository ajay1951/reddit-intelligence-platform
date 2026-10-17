import React, { useState, memo, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  BrainCircuit, 
  Database, 
  LineChart, 
  Search, 
  FileText, 
  CheckCircle2, 
  ShieldAlert, 
  Sparkles, 
  ArrowRight, 
  Copy, 
  Check, 
  Download, 
  StopCircle, 
  Layers, 
  Clock, 
  CheckCheck
} from 'lucide-react';
import { useSSE } from '../hooks/useSSE';
import { API_ENDPOINTS } from '../api/endpoints';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import './DeepResearch.css';

interface AgentStepProps {
  icon: React.ElementType;
  title: string;
  status: 'running' | 'complete' | 'error' | 'pending';
  message: string;
  isLast?: boolean;
}

const AgentStep = memo(({ icon: Icon, title, status, message, isLast = false }: AgentStepProps) => {
  return (
    <div className={`orchestrator-step ${status}`}>
      <div className="step-timeline-rail">
        <div className={`step-node-icon ${status}`}>
          {status === 'running' && <div className="step-spinner"></div>}
          {status === 'complete' && <CheckCircle2 size={16} className="text-emerald-600" />}
          {status === 'pending' && <Icon size={14} className="text-slate-400" />}
          {status === 'error' && <ShieldAlert size={16} className="text-red-500" />}
        </div>
        {!isLast && <div className={`step-connector-line ${status}`}></div>}
      </div>

      <div className="step-content-box">
        <div className="step-title-row">
          <span className="step-label">{title}</span>
          <span className={`step-status-chip ${status}`}>
            {status === 'running' ? 'In Progress' : status === 'complete' ? 'Completed' : status === 'error' ? 'Failed' : 'Queued'}
          </span>
        </div>
        <p className="step-message-text">{message || 'Awaiting agent execution...'}</p>
      </div>
    </div>
  );
});

AgentStep.displayName = 'AgentStep';

interface ResearchStep {
  step: string;
  status: 'running' | 'complete' | 'error' | 'pending';
  message: string;
}

const RESEARCH_PROMPTS = [
  'What are the biggest complaints about Docker and containers in Enterprise?',
  'Analyze developer sentiment on React Server Components vs traditional client SPAs.',
  'Identify top failure modes in Python production microservices from Reddit engineering discussions.',
  'Summarize sentiment on remote engineering compensation and market salary expectations.'
];

export default function DeepResearch() {
  const [topic, setTopic] = useState('');
  const [steps, setSteps] = useState<ResearchStep[]>([]);
  const [finalReport, setFinalReport] = useState('');
  const [copied, setCopied] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const { isStreaming, error, startStream, stopStream } = useSSE(API_ENDPOINTS.DEEP_RESEARCH);

  useEffect(() => {
    if (isStreaming) {
      setElapsedSeconds(0);
      timerRef.current = setInterval(() => {
        setElapsedSeconds(prev => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isStreaming]);

  const handleResearch = async (e?: React.FormEvent, customTopic?: string) => {
    if (e) e.preventDefault();
    const query = customTopic || topic;
    if (!query.trim() || isStreaming) return;

    if (customTopic) setTopic(customTopic);
    setSteps([]);
    setFinalReport('');

    await startStream(
      { topic: query },
      (event: any) => {
        if (event.step === 'final') {
          setFinalReport(event.data);
          return;
        }
        if (event.step === 'error' || event.status === 'error') {
          setSteps(prev => {
            const hasRunning = prev.some(s => s.status === 'running');
            if (hasRunning) {
              return prev.map(s => s.status === 'running' ? { ...s, status: 'error', message: event.message || s.message } : s);
            }
            return [...prev, { step: 'error', status: 'error', message: event.message || 'Execution error' }];
          });
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
      }
    );
  };

  const getIconForStep = (stepName: string) => {
    if (stepName.includes('research')) return Search;
    if (stepName.includes('trend')) return LineChart;
    if (stepName.includes('sentiment')) return BrainCircuit;
    if (stepName.includes('verif')) return ShieldAlert;
    if (stepName.includes('reflect')) return Sparkles;
    if (stepName.includes('report')) return FileText;
    return Database;
  };

  const handleCopyReport = () => {
    if (!finalReport) return;
    navigator.clipboard.writeText(finalReport);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadMarkdown = () => {
    if (!finalReport) return;
    const blob = new Blob([finalReport], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reddit-intelligence-report-${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="deep-research-workspace">
      {/* Page Header */}
      <div className="research-page-header animate-fade-in">
        <div>
          <h1 className="page-title">
            <span>Deep Research Studio</span>
          </h1>
          <p className="subtitle">
            Autonomous multi-agent synthesis: Ingestion, Trend Analysis, Sentiment Mining & Evidence Verification.
          </p>
        </div>
      </div>

      {/* Query Control Bar Card */}
      <Card className="query-control-card animate-fade-in delay-100">
        <form onSubmit={handleResearch} className="query-form">
          <div className="query-input-wrap">
            <Search size={18} className="text-slate-400" />
            <input 
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. What are developers saying about FastAPI vs Go in production?"
              disabled={isStreaming}
              className="query-text-input"
            />
          </div>

          <div className="query-btn-row">
            {!isStreaming ? (
              <Button type="submit" disabled={!topic.trim()} className="btn-primary">
                <span>Deploy Agent Swarm</span>
                <ArrowRight size={16} />
              </Button>
            ) : (
              <Button type="button" variant="danger" onClick={stopStream}>
                <StopCircle size={16} />
                <span>Abort Swarm</span>
              </Button>
            )}
          </div>
        </form>

        {/* Suggestion Chips */}
        <div className="query-suggestions-strip">
          <span className="strip-label">
            <Sparkles size={12} className="text-indigo-600" />
            <span>Suggested Research Topics:</span>
          </span>
          <div className="strip-pills">
            {RESEARCH_PROMPTS.map((p, idx) => (
              <button
                key={idx}
                type="button"
                className="strip-pill-btn"
                onClick={() => handleResearch(undefined, p)}
                disabled={isStreaming}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="research-error-banner">
            <ShieldAlert size={16} />
            <span>{error}</span>
          </div>
        )}
      </Card>

      {/* Main Studio Grid: Left Stepper (1/3), Right Dossier (2/3) */}
      <div className="studio-layout-grid animate-fade-in delay-200">
        
        {/* Left Column: Multi-Agent Orchestration Stepper */}
        <Card className="orchestration-card">
          <div className="orchestration-header">
            <div className="orchestration-title-wrap">
              <BrainCircuit size={18} className="text-indigo-600" />
              <h2 className="orchestration-title">Agent Orchestrator</h2>
            </div>
            {isStreaming && (
              <div className="orchestrator-timer tabular-nums">
                <Clock size={12} />
                <span>{elapsedSeconds}s</span>
              </div>
            )}
          </div>

          <div className="orchestrator-pipeline">
            {steps.length === 0 && !isStreaming ? (
              <div className="orchestrator-idle-state">
                <Layers size={28} className="text-slate-300 mb-2" />
                <p className="idle-title">Swarm Standby</p>
                <p className="idle-desc">Deploy a research topic to activate retrieval, sentiment, and claim verification agents.</p>
              </div>
            ) : (
              steps.map((step, idx) => (
                <AgentStep 
                  key={idx}
                  icon={getIconForStep(step.step)}
                  title={step.step.replace(/_/g, ' ').toUpperCase()}
                  status={step.status as any}
                  message={step.message}
                  isLast={idx === steps.length - 1}
                />
              ))
            )}
          </div>
        </Card>

        {/* Right Column: Executive Research Dossier */}
        <Card className="dossier-card">
          <div className="dossier-header-bar">
            <div>
              <h2 className="dossier-title">Executive Research Brief</h2>
              <p className="dossier-sub">Grounded synthesis compiled with evidence verification scorecard.</p>
            </div>

            {finalReport && (
              <div className="dossier-action-buttons">
                <button 
                  className="btn btn-secondary btn-sm"
                  onClick={handleCopyReport}
                  title="Copy markdown text"
                >
                  {copied ? (
                    <>
                      <CheckCheck size={14} className="text-emerald-600" />
                      <span className="text-emerald-600">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy size={14} />
                      <span>Copy</span>
                    </>
                  )}
                </button>
                <button 
                  className="btn btn-secondary btn-sm"
                  onClick={handleDownloadMarkdown}
                  title="Export Markdown report"
                >
                  <Download size={14} />
                  <span>Export .md</span>
                </button>
              </div>
            )}
          </div>

          <div className="dossier-content-area">
            {!finalReport && !isStreaming && (error || steps.some(s => s.status === 'error')) && (
              <div className="dossier-error-state animate-fade-in">
                <div className="dossier-error-icon">
                  <ShieldAlert size={24} />
                </div>
                <h3 className="dossier-error-title">Synthesis Interrupted</h3>
                <p className="dossier-error-desc">
                  {error || steps.find(s => s.status === 'error')?.message || 'The research swarm encountered an error during intelligence synthesis.'}
                </p>
                <Button 
                  variant="secondary" 
                  size="sm"
                  onClick={() => handleResearch()}
                >
                  Retry Synthesis
                </Button>
              </div>
            )}

            {!finalReport && !isStreaming && !error && !steps.some(s => s.status === 'error') && (
              <div className="dossier-placeholder">
                <FileText size={36} className="text-slate-300 mb-3" />
                <h3 className="placeholder-title">Awaiting Synthesis</h3>
                <p className="placeholder-desc">
                  Select or submit a research query to generate a structured executive brief with verified Reddit citations.
                </p>
              </div>
            )}

            {isStreaming && !finalReport && (
              <div className="dossier-streaming-loader">
                <div className="loader-orbit">
                  <div className="orbit-spinner"></div>
                  <BrainCircuit size={28} className="text-indigo-600" />
                </div>
                <h3 className="loader-title">Synthesizing Market Intelligence</h3>
                <p className="loader-desc">
                  Agents are analyzing discussion trees and cross-referencing claim grounding...
                </p>
              </div>
            )}

            {finalReport && (
              <div className="dossier-markdown-view animate-fade-in">
                <ReactMarkdown>{finalReport}</ReactMarkdown>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
