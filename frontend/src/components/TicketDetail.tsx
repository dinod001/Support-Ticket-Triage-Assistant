import React, { useEffect, useState, useCallback } from 'react';
import { ticketsApi } from '../services/api';
import { Ticket } from '../types/ticket';
import {
  ArrowLeft,
  Save,
  CheckCircle,
  Copy,
  Clock,
  Mail,
  BookOpen,
  Sparkles,
  Bot,
  AlertTriangle,
  Play,
  RotateCcw,
  Check,
  Trash2
} from 'lucide-react';

interface TicketDetailProps {
  ticketId: number;
  onBack: () => void;
  onTicketUpdated?: () => void;
}

const CATEGORIES = [
  'Refund',
  'Shipping',
  'Damaged',
  'Technical',
  'Account',
  'Billing',
  'needs manual triage',
];

const PRIORITIES = ['urgent', 'high', 'medium', 'low'];
const STATUSES = ['open', 'in_progress', 'resolved', 'closed'];

export const TicketDetail: React.FC<TicketDetailProps> = ({ ticketId, onBack, onTicketUpdated }) => {
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [deleting, setDeleting] = useState<boolean>(false);
  const [streaming, setStreaming] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  // Editable Form State
  const [status, setStatus] = useState<string>('open');
  const [category, setCategory] = useState<string>('');
  const [priority, setPriority] = useState<string>('medium');
  const [draftReply, setDraftReply] = useState<string>('');
  const [agentNotes, setAgentNotes] = useState<string>('');

  const loadTicket = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await ticketsApi.getTicket(ticketId);
      setTicket(data);
      setStatus(data.status);
      setCategory(data.category || 'Refund');
      setPriority(data.priority || 'medium');
      setDraftReply(data.draft_reply || '');
      setAgentNotes(data.agent_notes || '');
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to load ticket.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  }, [ticketId]);

  useEffect(() => {
    loadTicket();
  }, [loadTicket]);

  const handleSave = async (overrideStatus?: string) => {
    setSaving(true);
    setError(null);
    setSuccessMsg(null);

    const targetStatus = overrideStatus || status;

    try {
      const updated = await ticketsApi.updateTicket(ticketId, {
        status: targetStatus,
        category,
        priority,
        draft_reply: draftReply,
        agent_notes: agentNotes,
      });
      setTicket(updated);
      setStatus(updated.status);
      setSuccessMsg(overrideStatus === 'resolved' ? 'Ticket resolved and saved!' : 'Changes saved successfully!');
      if (onTicketUpdated) {
        onTicketUpdated();
      }
      setTimeout(() => setSuccessMsg(null), 3500);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to update ticket.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setSaving(false);
    }
  };

  const handleCopyDraft = () => {
    if (!draftReply) return;
    navigator.clipboard.writeText(draftReply);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleStreamDraft = () => {
    if (streaming) return;
    setStreaming(true);
    setDraftReply(''); // Clear for live stream typing
    setError(null);

    ticketsApi.streamDraft(
      ticketId,
      (token) => {
        setDraftReply((prev) => prev + token);
      },
      (fullDraft, citations) => {
        setDraftReply(fullDraft);
        setStreaming(false);
        if (ticket) {
          setTicket({ ...ticket, cited_articles: citations });
        }
      },
      (err) => {
        console.error('Streaming failed:', err);
        setStreaming(false);
        setError('Streaming connection interrupted. Retaining last response.');
      }
    );
  };

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to permanently delete Ticket #${ticketId}? This action cannot be undone.`)) {
      return;
    }
    setDeleting(true);
    setError(null);
    try {
      await ticketsApi.deleteTicket(ticketId);
      onTicketUpdated?.();
      onBack();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to delete ticket.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto py-16 px-4 flex flex-col items-center justify-center text-slate-500">
        <RotateCcw className="w-8 h-8 animate-spin text-blue-600 mb-3" />
        <p className="text-sm font-medium">Loading ticket details & AI context...</p>
      </div>
    );
  }

  if (error && !ticket) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4">
        <button
          onClick={onBack}
          className="inline-flex items-center text-xs font-semibold text-blue-600 hover:text-blue-800 mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to Ticket List
        </button>
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center space-x-3">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
          <p className="text-sm text-rose-700 font-medium">{error}</p>
        </div>
      </div>
    );
  }

  if (!ticket) return null;

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      {/* Top Navigation & Status Bar */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <button
          onClick={onBack}
          className="inline-flex items-center text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to All Tickets
        </button>

        <div className="flex items-center space-x-3">
          {/* Status Dropdown */}
          <div className="flex items-center space-x-2">
            <span className="text-xs font-medium text-slate-500">Status:</span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="text-xs font-semibold rounded-lg border border-slate-300 py-1.5 px-3 bg-white text-slate-800 shadow-xs focus:ring-2 focus:ring-blue-500"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace('_', ' ').toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          {/* Quick Resolve Button */}
          {status !== 'resolved' && (
            <button
              onClick={() => handleSave('resolved')}
              disabled={saving}
              className="inline-flex items-center px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 shadow-xs transition-colors disabled:opacity-50"
            >
              <CheckCircle className="w-3.5 h-3.5 mr-1.5" />
              Resolve Ticket
            </button>
          )}

          {/* Save Button */}
          <button
            onClick={() => handleSave()}
            disabled={saving}
            className="inline-flex items-center px-4 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 shadow-xs transition-colors disabled:opacity-50"
          >
            <Save className={`w-3.5 h-3.5 mr-1.5 ${saving ? 'animate-spin' : ''}`} />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>

          {/* Delete Ticket Button */}
          <button
            onClick={handleDelete}
            disabled={saving || deleting}
            className="inline-flex items-center px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200 shadow-xs transition-colors disabled:opacity-50"
            title="Permanently delete ticket"
          >
            <Trash2 className={`w-3.5 h-3.5 mr-1.5 ${deleting ? 'animate-spin' : ''}`} />
            {deleting ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>

      {/* Success / Error Banners */}
      {successMsg && (
        <div className="mb-6 p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs font-semibold text-emerald-800 flex items-center">
          <Check className="w-4 h-4 mr-2 text-emerald-600" />
          {successMsg}
        </div>
      )}
      {error && (
        <div className="mb-6 p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs font-semibold text-rose-800 flex items-center">
          <AlertTriangle className="w-4 h-4 mr-2 text-rose-600" />
          {error}
        </div>
      )}

      {/* Main Grid: Left (Customer & Triage) vs Right (RAG & Reply) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (5 cols): Triage Cards & Inbound Ticket */}
        <div className="lg:col-span-5 space-y-6">
          {/* Ticket Header & Metadata */}
          <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
              <span className="font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                Ticket #{ticket.id}
              </span>
              <span className="flex items-center">
                <Clock className="w-3.5 h-3.5 mr-1 text-slate-400" />
                {new Date(ticket.created_at).toLocaleString()}
              </span>
            </div>

            <h1 className="text-lg font-bold text-slate-900 mb-2">{ticket.title}</h1>

            {ticket.customer_email && (
              <div className="flex items-center text-xs text-slate-600 mb-4">
                <Mail className="w-3.5 h-3.5 mr-1.5 text-slate-400" />
                <span className="font-medium">{ticket.customer_email}</span>
              </div>
            )}

            {/* Inbound Customer Message */}
            <div className="mt-4 pt-4 border-t border-slate-100">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-2">
                Inbound Customer Message
              </span>
              <div className="p-3.5 bg-slate-50 rounded-lg text-xs leading-relaxed text-slate-800 whitespace-pre-wrap border border-slate-100">
                {ticket.description}
              </div>
            </div>
          </div>

          {/* AI Triage Analysis Card */}
          <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-100">
              <Sparkles className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-bold text-slate-900">AI Triage Classification</h2>
            </div>

            {/* Editable Category & Priority */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                  Category
                </label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 bg-white font-medium text-slate-800 focus:ring-2 focus:ring-blue-500"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                  Priority
                </label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 bg-white font-medium text-slate-800 focus:ring-2 focus:ring-blue-500"
                >
                  {PRIORITIES.map((p) => (
                    <option key={p} value={p}>
                      {p.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Sentiment & Summary */}
            <div>
              <span className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Detected Sentiment
              </span>
              <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-medium bg-slate-100 text-slate-700 capitalize">
                {ticket.sentiment || 'neutral'}
              </span>
            </div>

            {ticket.summary && (
              <div>
                <span className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                  Executive AI Summary
                </span>
                <p className="text-xs text-slate-700 bg-blue-50/60 p-2.5 rounded-lg border border-blue-100">
                  {ticket.summary}
                </p>
              </div>
            )}

            {/* Extracted Entities */}
            {ticket.entities && Object.keys(ticket.entities).length > 0 && (
              <div>
                <span className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                  Extracted Entities (Structured Data)
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(ticket.entities).map(([k, v]) =>
                    v ? (
                      <span
                        key={k}
                        className="inline-flex items-center px-2 py-1 rounded-md text-[11px] bg-indigo-50 text-indigo-700 border border-indigo-100 font-mono"
                      >
                        <span className="font-semibold text-indigo-900 mr-1">{k}:</span>
                        {String(v)}
                      </span>
                    ) : null
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Internal Agent Notes */}
          <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-xs">
            <span className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
              Internal Agent Notes (Private)
            </span>
            <textarea
              rows={3}
              value={agentNotes}
              onChange={(e) => setAgentNotes(e.target.value)}
              placeholder="Add internal notes for teammates (e.g. 'Waiting for courier tracking update')."
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 placeholder-slate-400"
            />
          </div>
        </div>

        {/* Right Column (7 cols): RAG Policy Citations & Draft Reply Assistant */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-xs space-y-4">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
              <div className="flex items-center space-x-2">
                <Bot className="w-5 h-5 text-indigo-600" />
                <h2 className="text-sm font-bold text-slate-900">RAG AI Response Assistant</h2>
              </div>

              {/* Streaming Re-generate button (Stretch Goal) */}
              <button
                type="button"
                onClick={handleStreamDraft}
                disabled={streaming}
                title="Streams draft reply token-by-token via Server-Sent Events (SSE)"
                className="inline-flex items-center px-2.5 py-1 rounded text-xs font-medium bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition-colors disabled:opacity-50"
              >
                <Play className={`w-3 h-3 mr-1 ${streaming ? 'animate-spin' : ''}`} />
                {streaming ? 'Streaming Draft...' : 'Stream New Draft (SSE)'}
              </button>
            </div>

            {/* Cited Articles Box */}
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 flex items-center mb-2">
                <BookOpen className="w-3.5 h-3.5 mr-1 text-slate-400" />
                Cited Knowledge Base Articles (RAG Evidence)
              </span>
              {ticket.cited_articles && ticket.cited_articles.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {ticket.cited_articles.map((article, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200"
                    >
                      <Check className="w-3 h-3 mr-1 text-emerald-600" />
                      {article}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic">
                  No direct knowledge base policy matched with high confidence. Fallback response generated.
                </p>
              )}
            </div>

            {/* Draft Reply Textarea */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  Agent-Editable Customer Draft Reply
                </label>
                <button
                  type="button"
                  onClick={handleCopyDraft}
                  className="inline-flex items-center text-xs text-slate-500 hover:text-slate-800 font-medium"
                >
                  <Copy className="w-3.5 h-3.5 mr-1" />
                  {copied ? 'Copied!' : 'Copy to Clipboard'}
                </button>
              </div>

              <textarea
                rows={12}
                value={draftReply}
                onChange={(e) => setDraftReply(e.target.value)}
                placeholder="The AI will draft a reply based on knowledge base policies. You can edit this reply directly before responding."
                className="w-full px-3.5 py-3 text-xs leading-relaxed rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 font-sans text-slate-800 bg-white"
              />
            </div>

            {/* Bottom Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-100">
              <span className="text-[11px] text-slate-400">
                Tip: Review citations and personalize the draft before saving or resolving.
              </span>

              <button
                type="button"
                onClick={() => handleSave()}
                disabled={saving}
                className="inline-flex items-center px-4 py-2 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-700 shadow-xs transition-colors disabled:opacity-50"
              >
                <Save className="w-3.5 h-3.5 mr-1.5" />
                {saving ? 'Saving...' : 'Save Draft Reply'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
