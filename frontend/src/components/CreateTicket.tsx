import React, { useState } from 'react';
import { ticketsApi } from '../services/api';
import { Ticket } from '../types/ticket';
import { Sparkles, Loader2, CheckCircle2, AlertCircle, ArrowRight, RefreshCw, Send } from 'lucide-react';

interface CreateTicketProps {
  onTicketCreated: (ticket: Ticket) => void;
}

const SAMPLE_TICKETS = [
  {
    label: 'Refund Request',
    badge: 'Refund',
    title: 'Requesting refund for unopened shoes',
    customer_email: 'sarah.j@example.com',
    description: 'Hi, I received my order #ORD-98214 on Monday, but the shoes are too tight. They are completely unworn in their original box. Can I get a full refund to my Visa card? Please advise.',
  },
  {
    label: 'Damaged Item',
    badge: 'Damaged',
    title: 'Screen arrived shattered in package',
    customer_email: 'alex.m@example.com',
    description: 'Extremely upset! I opened package #ORD-55412 today and the monitor display is cracked straight down the middle. Tracking was TRK-88219. I need an urgent replacement immediately!',
  },
  {
    label: 'Shipping Delay',
    badge: 'Shipping',
    title: 'Package delayed over 10 business days',
    customer_email: 'david.k@example.com',
    description: 'Hello, my express shipment with tracking number TRK-99014 was estimated for arrival 5 days ago. The courier portal has not updated. Where is my delivery?',
  },
  {
    label: 'Password Reset',
    badge: 'Account',
    title: 'Locked out of account, 2FA code not arriving',
    customer_email: 'clara.b@example.com',
    description: 'I cannot log into my workspace account. The password reset link expires before I receive it, and my SMS 2FA code is not coming through. Please assist urgently.',
  },
];

export const CreateTicket: React.FC<CreateTicketProps> = ({ onTicketCreated }) => {
  const [title, setTitle] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [createdTicket, setCreatedTicket] = useState<Ticket | null>(null);

  const applySample = (sample: typeof SAMPLE_TICKETS[0]) => {
    setTitle(sample.title);
    setCustomerEmail(sample.customer_email);
    setDescription(sample.description);
    setError(null);
    setCreatedTicket(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      setError('Please provide both a ticket title and a detailed description.');
      return;
    }

    setLoading(true);
    setError(null);
    setCreatedTicket(null);

    // Dynamic loading messages to show AI pipeline stages
    setLoadingStep('1/3: Analyzing ticket intent, priority & sentiment with LLM...');
    const step2Timer = setTimeout(() => {
      setLoadingStep('2/3: Searching knowledge base vector embeddings for matching policies...');
    }, 1800);
    const step3Timer = setTimeout(() => {
      setLoadingStep('3/3: Drafting empathetic, policy-cited customer reply...');
    }, 3800);

    try {
      const ticket = await ticketsApi.createTicket({
        title: title.trim(),
        description: description.trim(),
        customer_email: customerEmail.trim() || undefined,
      });

      clearTimeout(step2Timer);
      clearTimeout(step3Timer);
      setLoading(false);
      setCreatedTicket(ticket);
    } catch (err: any) {
      clearTimeout(step2Timer);
      clearTimeout(step3Timer);
      setLoading(false);
      const msg = err.response?.data?.detail || err.message || 'Failed to submit ticket. Please ensure backend is reachable.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
  };

  const handleReset = () => {
    setTitle('');
    setCustomerEmail('');
    setDescription('');
    setError(null);
    setCreatedTicket(null);
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center">
          <Sparkles className="w-6 h-6 mr-2 text-blue-600" />
          Submit Customer Support Ticket
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Incoming inquiries are automatically triaged by the LLM (Category, Priority, Sentiment, Entities) and paired with an AI-generated draft response backed by our Knowledge Base.
        </p>
      </div>

      {/* Quick Test Samples */}
      <div className="mb-6 p-4 bg-slate-50 border border-slate-200 rounded-xl">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2.5">
          Quick Prefill Samples (Click to Test)
        </div>
        <div className="flex flex-wrap gap-2">
          {SAMPLE_TICKETS.map((sample) => (
            <button
              key={sample.label}
              type="button"
              onClick={() => applySample(sample)}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-slate-300 text-slate-700 hover:border-blue-500 hover:text-blue-600 hover:shadow-xs transition-all flex items-center space-x-1.5"
            >
              <span className="font-semibold text-blue-600">[{sample.badge}]</span>
              <span>{sample.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Success Notification Box */}
      {createdTicket && (
        <div className="mb-6 p-5 bg-emerald-50 border border-emerald-200 rounded-xl">
          <div className="flex items-start">
            <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0 mt-0.5" />
            <div className="ml-3 flex-1">
              <h3 className="text-sm font-semibold text-emerald-900">
                Ticket #{createdTicket.id} Created & Triaged Successfully!
              </h3>
              <p className="mt-1 text-xs text-emerald-700">
                AI Category: <span className="font-semibold">{createdTicket.category}</span> • Priority: <span className="font-semibold uppercase">{createdTicket.priority}</span> • Sentiment: <span className="font-semibold">{createdTicket.sentiment}</span>
              </p>
              <div className="mt-4 flex items-center space-x-3">
                <button
                  type="button"
                  onClick={() => onTicketCreated(createdTicket)}
                  className="inline-flex items-center px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 shadow-xs transition-colors"
                >
                  Review AI Draft in Detail View
                  <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  className="px-3 py-2 text-xs font-medium text-emerald-800 hover:text-emerald-900 hover:underline"
                >
                  Submit Another
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error Notification */}
      {error && (
        <div className="mb-6 p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="ml-3">
            <h4 className="text-sm font-semibold text-rose-900">Submission Error</h4>
            <p className="text-xs text-rose-700 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Ticket Form */}
      <div className="bg-white rounded-xl shadow-xs border border-slate-200 overflow-hidden">
        <form onSubmit={handleSubmit} className="p-6 sm:p-8 space-y-6">
          {/* Customer Email */}
          <div>
            <label htmlFor="customer_email" className="block text-sm font-medium text-slate-700 mb-1">
              Customer Email <span className="text-slate-400 font-normal">(Optional)</span>
            </label>
            <input
              type="email"
              id="customer_email"
              value={customerEmail}
              onChange={(e) => setCustomerEmail(e.target.value)}
              placeholder="customer@example.com"
              disabled={loading}
              className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white placeholder-slate-400 disabled:bg-slate-50 disabled:text-slate-500"
            />
          </div>

          {/* Ticket Title */}
          <div>
            <label htmlFor="title" className="block text-sm font-medium text-slate-700 mb-1">
              Ticket Subject / Title <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              id="title"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Return authorization request for order #1234"
              disabled={loading}
              className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white placeholder-slate-400 disabled:bg-slate-50 disabled:text-slate-500"
            />
          </div>

          {/* Ticket Description */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-slate-700 mb-1">
              Customer Message / Issue Description <span className="text-rose-500">*</span>
            </label>
            <textarea
              id="description"
              required
              rows={6}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the issue in full detail. The AI engine will extract order numbers, assess urgency, and draft an empathetic response based on company policies."
              disabled={loading}
              className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white placeholder-slate-400 disabled:bg-slate-50 disabled:text-slate-500 font-normal"
            />
          </div>

          {/* Loading Progress State */}
          {loading && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-center space-x-3 animate-pulse">
              <Loader2 className="w-5 h-5 text-blue-600 animate-spin shrink-0" />
              <div className="flex-1">
                <p className="text-xs font-semibold text-blue-900">AI Triage & RAG in Progress</p>
                <p className="text-xs text-blue-700 mt-0.5">{loadingStep}</p>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={handleReset}
              disabled={loading}
              className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-900 transition-colors flex items-center space-x-1"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1" />
              Clear Fields
            </button>

            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center px-6 py-2.5 rounded-lg text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Processing AI Triage...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Submit Ticket
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
