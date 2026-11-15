import React, { useEffect, useState, useCallback } from 'react';
import { ticketsApi } from '../services/api';
import { Ticket } from '../types/ticket';
import {
  Search,
  Filter,
  RefreshCw,
  Clock,
  Mail,
  ChevronRight,
  AlertTriangle,
  Smile,
  Meh,
  Frown,
  Flame,
  Inbox,
  Trash2
} from 'lucide-react';

interface TicketListProps {
  onSelectTicket: (ticketId: number) => void;
  onRefreshCount?: (count: number) => void;
}

const CATEGORIES = [
  'All',
  'Refund',
  'Shipping',
  'Damaged',
  'Technical',
  'Account',
  'Billing',
  'needs manual triage',
];

const PRIORITIES = ['All', 'urgent', 'high', 'medium', 'low'];
const STATUSES = ['All', 'open', 'in_progress', 'resolved', 'closed'];

export const TicketList: React.FC<TicketListProps> = ({ onSelectTicket, onRefreshCount }) => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter States
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [categoryFilter, setCategoryFilter] = useState<string>('All');
  const [priorityFilter, setPriorityFilter] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const fetchTickets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await ticketsApi.getTickets({
        status: statusFilter !== 'All' ? statusFilter : undefined,
        category: categoryFilter !== 'All' ? categoryFilter : undefined,
        priority: priorityFilter !== 'All' ? priorityFilter : undefined,
        search: searchQuery.trim() || undefined,
        limit: 50,
      });
      setTickets(data.tickets);
      setTotal(data.total);
      if (onRefreshCount) {
        onRefreshCount(data.total);
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to fetch tickets from backend.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  }, [statusFilter, categoryFilter, priorityFilter, searchQuery, onRefreshCount]);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  const resetFilters = () => {
    setStatusFilter('All');
    setCategoryFilter('All');
    setPriorityFilter('All');
    setSearchQuery('');
  };

  const handleDeleteTicket = async (e: React.MouseEvent, ticketId: number) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to permanently delete Ticket #${ticketId}?`)) {
      return;
    }
    try {
      await ticketsApi.deleteTicket(ticketId);
      fetchTickets();
    } catch (err: any) {
      alert('Failed to delete ticket: ' + (err.response?.data?.detail || err.message));
    }
  };

  const getPriorityBadge = (priority?: string | null) => {
    switch (priority?.toLowerCase()) {
      case 'urgent':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">
            <Flame className="w-3 h-3 mr-1 text-rose-600" />
            URGENT
          </span>
        );
      case 'high':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">
            HIGH
          </span>
        );
      case 'medium':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
            MEDIUM
          </span>
        );
      case 'low':
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
            LOW
          </span>
        );
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'open':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-100 text-sky-800">
            ● Open
          </span>
        );
      case 'in_progress':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">
            ● In Progress
          </span>
        );
      case 'resolved':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
            ✓ Resolved
          </span>
        );
      case 'closed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-200 text-slate-700">
            Closed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  const getSentimentBadge = (sentiment?: string | null) => {
    switch (sentiment?.toLowerCase()) {
      case 'frustrated':
      case 'negative':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200" title="Frustrated/Negative Customer">
            <Frown className="w-3 h-3 mr-1 text-rose-500" />
            {sentiment}
          </span>
        );
      case 'positive':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <Smile className="w-3 h-3 mr-1 text-emerald-500" />
            Positive
          </span>
        );
      case 'neutral':
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-50 text-slate-600 border border-slate-200">
            <Meh className="w-3 h-3 mr-1 text-slate-400" />
            {sentiment || 'Neutral'}
          </span>
        );
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center">
            <Inbox className="w-6 h-6 mr-2 text-blue-600" />
            Triage & Ticket Dashboard
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Manage incoming customer support tickets triaged by LLM classification and RAG retrieval.
          </p>
        </div>
        <div className="mt-4 sm:mt-0 flex items-center space-x-3">
          <span className="text-xs font-medium text-slate-500">
            Total Tickets: <span className="font-bold text-slate-800">{total}</span>
          </span>
          <button
            onClick={fetchTickets}
            disabled={loading}
            className="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 hover:border-slate-400 shadow-xs transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs mb-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search title, description..."
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white placeholder-slate-400"
            />
          </div>

          {/* Status Filter */}
          <div>
            <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-slate-800"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s === 'All' ? 'All Statuses' : s}
                </option>
              ))}
            </select>
          </div>

          {/* Category Filter */}
          <div>
            <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
              Category
            </label>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-slate-800"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c === 'All' ? 'All Categories' : c}
                </option>
              ))}
            </select>
          </div>

          {/* Priority Filter */}
          <div>
            <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
              Priority
            </label>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-slate-800"
            >
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p === 'All' ? 'All Priorities' : p.toUpperCase()}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Clear Filters Button */}
        {(statusFilter !== 'All' || categoryFilter !== 'All' || priorityFilter !== 'All' || searchQuery) && (
          <div className="flex justify-end pt-2 border-t border-slate-100">
            <button
              onClick={resetFilters}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center"
            >
              <Filter className="w-3.5 h-3.5 mr-1" />
              Reset All Filters
            </button>
          </div>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 mb-6 bg-rose-50 border border-rose-200 rounded-xl flex items-center space-x-3">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
          <p className="text-xs text-rose-700 font-medium">{error}</p>
        </div>
      )}

      {/* Loading state */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center text-slate-500">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mb-3" />
          <p className="text-sm font-medium">Loading tickets from database...</p>
        </div>
      ) : tickets.length === 0 ? (
        /* Empty State */
        <div className="py-16 bg-white rounded-xl border border-dashed border-slate-300 text-center p-8">
          <Inbox className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-slate-800">No tickets found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            No support tickets match the selected filters. Try broadening your criteria or submit a new test ticket.
          </p>
          <button
            onClick={resetFilters}
            className="mt-4 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors"
          >
            Clear Active Filters
          </button>
        </div>
      ) : (
        /* Ticket Cards List */
        <div className="space-y-3">
          {tickets.map((ticket) => (
            <div
              key={ticket.id}
              onClick={() => onSelectTicket(ticket.id)}
              className="bg-white rounded-xl p-5 border border-slate-200 shadow-xs hover:border-blue-400 hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                {/* Left Side: ID, Title, Customer */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-1.5 flex-wrap gap-y-1">
                    <span className="text-xs font-mono font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                      #{ticket.id}
                    </span>
                    {getStatusBadge(ticket.status)}
                    {getPriorityBadge(ticket.priority)}
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
                      {ticket.category || 'Uncategorized'}
                    </span>
                    {getSentimentBadge(ticket.sentiment)}
                  </div>

                  <h2 className="text-base font-semibold text-slate-900 group-hover:text-blue-600 transition-colors line-clamp-1">
                    {ticket.title}
                  </h2>

                  <p className="text-xs text-slate-600 mt-1 line-clamp-2">
                    {ticket.summary || ticket.description}
                  </p>

                  <div className="mt-2.5 flex items-center space-x-4 text-xs text-slate-400">
                    {ticket.customer_email && (
                      <span className="flex items-center text-slate-500">
                        <Mail className="w-3.5 h-3.5 mr-1 text-slate-400" />
                        {ticket.customer_email}
                      </span>
                    )}
                    <span className="flex items-center">
                      <Clock className="w-3.5 h-3.5 mr-1 text-slate-400" />
                      {formatDate(ticket.created_at)}
                    </span>
                    {ticket.cited_articles && ticket.cited_articles.length > 0 && (
                      <span className="text-indigo-600 font-medium">
                        {ticket.cited_articles.length} KB source cited
                      </span>
                    )}
                  </div>
                </div>

                {/* Right Side: Action Button */}
                <div className="flex items-center space-x-2 shrink-0">
                  <button
                    onClick={(e) => handleDeleteTicket(e, ticket.id)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 border border-transparent hover:border-rose-200 transition-colors"
                    title="Delete ticket"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <div className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-50 text-slate-700 border border-slate-200 group-hover:bg-blue-600 group-hover:text-white group-hover:border-blue-600 transition-all">
                    <span>Review & Reply</span>
                    <ChevronRight className="w-3.5 h-3.5 ml-1" />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
