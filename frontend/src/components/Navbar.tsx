import React from 'react';
import { Bot, Inbox, PlusCircle, Sparkles } from 'lucide-react';

interface NavbarProps {
  activeTab: 'create' | 'list' | 'detail';
  onNavigate: (tab: 'create' | 'list') => void;
  ticketCount?: number;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, onNavigate, ticketCount = 0 }) => {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => onNavigate('list')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg text-slate-900 tracking-tight">AutoTriage AI</span>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
                  <Sparkles className="w-3 h-3 mr-1 text-blue-600" />
                  RAG Assistant
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">Aqlior Take-Home Assessment</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex space-x-2">
            <button
              onClick={() => onNavigate('list')}
              className={`flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'list' || activeTab === 'detail'
                  ? 'bg-blue-50 text-blue-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Inbox className="w-4 h-4 mr-2" />
              Triage Queue
              {ticketCount > 0 && (
                <span className="ml-2 px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-200 text-blue-800">
                  {ticketCount}
                </span>
              )}
            </button>

            <button
              onClick={() => onNavigate('create')}
              className={`flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'create'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-slate-700 hover:bg-slate-100'
              }`}
            >
              <PlusCircle className="w-4 h-4 mr-2" />
              New Ticket
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
};
