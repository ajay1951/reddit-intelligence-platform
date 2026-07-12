import React, { useState, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import { BrainCircuit, Database, LineChart, Search, FileText, CheckCircle2, ShieldAlert } from 'lucide-react';
import { useSSE } from '../hooks/useSSE';
import { API_ENDPOINTS } from '../api/endpoints';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import './DeepResearch.css';

interface AgentStepProps {
  icon: React.ElementType;
  title: string;
  status: 'running' | 'complete' | 'error' | 'pending';
  message: string;
}

const AgentStep = memo(({ icon: Icon, title, status, message }: AgentStepProps) => {
  return (
    <div className={`agent-step ${status} p-4 rounded-lg bg-[var(--card-bg)] border border-[var(--border-light)] flex items-start gap-4 mb-3 transition-all`}>
      <div className={`p-2 rounded-lg ${status === 'running' ? 'bg-blue-500/20 text-blue-400' : status === 'complete' ? 'bg-green-500/20 text-green-400' : 'bg-[var(--border-light)] text-[var(--text-secondary)]'}`}>
        <Icon size={24} />
      </div>
      <div className="flex-1">
        <h4 className="font-semibold text-[var(--text-primary)]">{title}</h4>
        <p className="text-sm text-[var(--text-secondary)] mt-1">{message}</p>
      </div>
      <div className="flex items-center justify-center w-8 h-8">
        {status === 'running' && <div className="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>}
        {status === 'complete' && <CheckCircle2 className="text-green-500" size={20} />}
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

export default function DeepResearch() {
  const [topic, setTopic] = useState('');
  const [steps, setSteps] = useState<ResearchStep[]>([]);
  const [finalReport, setFinalReport] = useState('');
  
  const { isStreaming, error, startStream, stopStream } = useSSE(API_ENDPOINTS.DEEP_RESEARCH);

  const handleResearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;

    setSteps([]);
    setFinalReport('');

    await startStream(
      { topic },
      (event: any) => {
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
      }
    );
  };

  const getIconForStep = (stepName: string) => {
    if (stepName.includes('research')) return Search;
    if (stepName.includes('trend')) return LineChart;
    if (stepName.includes('sentiment')) return BrainCircuit;
    if (stepName.includes('verification')) return ShieldAlert;
    if (stepName.includes('report')) return FileText;
    return Database;
  };

  return (
    <div className="deep-research-container max-w-6xl mx-auto">
      <div className="header mb-8 text-center animate-fade-in">
        <h1 className="text-3xl font-bold mb-2">Deep <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-300">Research Terminal</span></h1>
        <p className="text-[var(--text-secondary)]">Deploy a swarm of autonomous agents to synthesize market intelligence.</p>
      </div>

      <Card className="mb-8 p-6 animate-fade-in delay-100">
        <form onSubmit={handleResearch} className="flex gap-4">
          <Input 
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g., What are the biggest complaints about Docker in Enterprise?"
            disabled={isStreaming}
            className="flex-1"
          />
          <Button type="submit" isLoading={isStreaming}>
            Deploy Agents
          </Button>
          {isStreaming && (
            <Button type="button" variant="danger" onClick={stopStream}>
              Abort
            </Button>
          )}
        </form>
        {error && <p className="text-red-500 mt-2 text-sm">{error}</p>}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-4 animate-fade-in delay-200">
          <Card className="h-full p-4">
            <CardHeader className="mb-4 pb-2 border-b border-gray-800">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <BrainCircuit className="text-blue-400" size={20} />
                Agent Swarm Status
              </h3>
            </CardHeader>
            <div className="flex flex-col gap-2">
              {steps.length === 0 && !isStreaming && (
                <div className="text-center p-8 text-[var(--text-secondary)] border border-dashed border-gray-700 rounded-lg">
                  Awaiting deployment orders...
                </div>
              )}
              {steps.map((step, i) => (
                <AgentStep 
                  key={i}
                  icon={getIconForStep(step.step)}
                  title={step.step.replace('_', ' ').toUpperCase()}
                  status={step.status as any}
                  message={step.message}
                />
              ))}
            </div>
          </Card>
        </div>

        <div className="lg:col-span-8 animate-fade-in delay-300">
          <Card className="h-full min-h-[600px] p-6 relative">
            <CardHeader className="mb-4 pb-2 border-b border-gray-800">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <FileText className="text-cyan-400" size={20} />
                Executive Briefing
              </h3>
            </CardHeader>
            <div className="prose prose-invert prose-blue max-w-none">
              {!finalReport && !isStreaming && (
                <div className="flex flex-col items-center justify-center h-[400px] text-[var(--text-secondary)] opacity-50">
                  <FileText size={48} className="mb-4" />
                  <p>Report will be synthesized here.</p>
                </div>
              )}
              {isStreaming && !finalReport && (
                <div className="flex flex-col items-center justify-center h-[400px] text-blue-400 opacity-70">
                  <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mb-4"></div>
                  <p className="animate-pulse">Agents are working...</p>
                </div>
              )}
              {finalReport && (
                <div className="markdown-content animate-fade-in">
                  <ReactMarkdown>{finalReport}</ReactMarkdown>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
