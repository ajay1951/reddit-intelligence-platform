import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Database, RefreshCw, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card, CardHeader } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { useApi } from '../hooks/useApi';
import { API_ENDPOINTS } from '../api/endpoints';
import './Admin.css';

const scrapeSchema = z.object({
  subreddits: z.string().min(1, 'At least one subreddit is required'),
  postLimit: z.coerce.number().min(1).max(100000),
  commentLimit: z.coerce.number().min(0).max(100000),
  startDate: z.string().optional(),
  endDate: z.string().optional(),
});

type ScrapeFormData = z.infer<typeof scrapeSchema>;

interface StatusMessage {
  type: 'success' | 'error' | 'info';
  message: string;
}

export default function Admin() {
  const [status, setStatus] = useState<StatusMessage | null>(null);
  
  const { execute: executeScrape, loading: isScraping } = useApi();
  const { execute: executeReindex, loading: isReindexing } = useApi();

  const { register, handleSubmit, formState: { errors } } = useForm<ScrapeFormData>({
    resolver: zodResolver(scrapeSchema),
    defaultValues: {
      subreddits: 'MachineLearning, Python, datascience',
      postLimit: 25,
      commentLimit: 5,
      startDate: '',
      endDate: '',
    }
  });

  const onSubmitScrape = async (data: ScrapeFormData) => {
    setStatus({ type: 'info', message: 'Scraping in progress... this may take a moment.' });
    
    try {
      const subs = data.subreddits.split(',').map(s => s.trim());
      const res = await executeScrape('post', API_ENDPOINTS.SCRAPE_BATCH, {
        subreddits: subs,
        post_limit: data.postLimit,
        comment_limit: data.commentLimit,
        start_date: data.startDate,
        end_date: data.endDate
      });
      setStatus({ 
        type: 'success', 
        message: `Scrape task dispatched successfully! Check the dashboard shortly for updates. Task ID: ${res.task_id}` 
      });
    } catch (error) {
      setStatus({ type: 'error', message: 'Failed to run batch scrape.' });
    }
  };

  const handleReindex = async () => {
    setStatus({ type: 'info', message: 'Reindexing vectors... this uses the embedding API.' });
    
    try {
      const res = await executeReindex('post', API_ENDPOINTS.SEARCH_REINDEX);
      setStatus({ 
        type: 'success', 
        message: `Reindex complete! ${res.indexed_documents} documents indexed.` 
      });
    } catch (error) {
      setStatus({ type: 'error', message: 'Failed to reindex documents.' });
    }
  };

  return (
    <div className="admin-container">
      <h1 className="page-title">System <span className="gradient-text">Administration</span></h1>
      
      {status && (
        <div className={`status-alert ${status.type} mb-6 flex items-center gap-2 p-4 rounded-lg bg-white/40 border border-white/20 shadow-sm`}>
          <AlertCircle size={20} className={status.type === 'error' ? 'text-red-500' : status.type === 'success' ? 'text-green-500' : 'text-blue-500'} />
          <span className="text-[var(--text-primary)] font-medium">{status.message}</span>
        </div>
      )}

      <div className="admin-grid grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="admin-card p-6">
          <CardHeader className="flex items-center gap-3 mb-4">
            <Database className="text-blue-400" size={24} />
            <h3 className="text-xl font-semibold">Batch Scraper</h3>
          </CardHeader>
          <p className="text-[var(--text-secondary)] mb-6 text-sm">Trigger a massive data extraction from Reddit subreddits.</p>
          
          <form onSubmit={handleSubmit(onSubmitScrape)} className="flex flex-col gap-4">
            <Input 
              label="Subreddits (comma separated)"
              {...register('subreddits')}
              error={errors.subreddits?.message}
              disabled={isScraping || isReindexing}
            />
            
            <div className="grid grid-cols-2 gap-4">
              <Input 
                label="Post Limit per Subreddit"
                type="number"
                {...register('postLimit')}
                error={errors.postLimit?.message}
                disabled={isScraping || isReindexing}
              />
              <Input 
                label="Comment Limit per Post"
                type="number"
                {...register('commentLimit')}
                error={errors.commentLimit?.message}
                disabled={isScraping || isReindexing}
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <Input 
                label="Start Date (Optional)"
                type="date"
                {...register('startDate')}
                disabled={isScraping || isReindexing}
              />
              <Input 
                label="End Date (Optional)"
                type="date"
                {...register('endDate')}
                disabled={isScraping || isReindexing}
              />
            </div>
            
            <Button type="submit" isLoading={isScraping} className="mt-2">
              Run Batch Scrape
            </Button>
          </form>
        </Card>

        <Card className="admin-card p-6">
          <CardHeader className="flex items-center gap-3 mb-4">
            <RefreshCw className="text-purple-400" size={24} />
            <h3 className="text-xl font-semibold">Vector Reindex</h3>
          </CardHeader>
          <p className="text-[var(--text-secondary)] mb-6 text-sm">Generate embeddings for all new posts and comments to update the RAG AI's knowledge base.</p>
          
          <div className="flex flex-col gap-4">
            <Button onClick={handleReindex} variant="secondary" isLoading={isReindexing}>
              Trigger Full Reindex
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
