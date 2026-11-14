import { useState } from 'react';
import { Navbar } from './components/Navbar';
import { TicketList } from './components/TicketList';
import { CreateTicket } from './components/CreateTicket';
import { TicketDetail } from './components/TicketDetail';
import { Ticket } from './types/ticket';

export function App() {
  const [activeTab, setActiveTab] = useState<'create' | 'list' | 'detail'>('list');
  const [selectedTicketId, setSelectedTicketId] = useState<number | null>(null);
  const [ticketCount, setTicketCount] = useState<number>(0);

  const handleNavigate = (tab: 'create' | 'list') => {
    setActiveTab(tab);
    if (tab === 'list') {
      setSelectedTicketId(null);
    }
  };

  const handleSelectTicket = (id: number) => {
    setSelectedTicketId(id);
    setActiveTab('detail');
  };

  const handleTicketCreated = (newTicket: Ticket) => {
    setSelectedTicketId(newTicket.id);
    setActiveTab('detail');
    setTicketCount((prev) => prev + 1);
  };

  const handleBackToList = () => {
    setActiveTab('list');
    setSelectedTicketId(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900 selection:bg-blue-100 selection:text-blue-900">
      <Navbar
        activeTab={activeTab}
        onNavigate={handleNavigate}
        ticketCount={ticketCount}
      />

      <main className="flex-1 pb-16">
        {activeTab === 'create' && (
          <CreateTicket onTicketCreated={handleTicketCreated} />
        )}

        {activeTab === 'list' && (
          <TicketList
            onSelectTicket={handleSelectTicket}
            onRefreshCount={(count) => setTicketCount(count)}
          />
        )}

        {activeTab === 'detail' && selectedTicketId !== null && (
          <TicketDetail
            ticketId={selectedTicketId}
            onBack={handleBackToList}
            onTicketUpdated={() => {}}
          />
        )}
      </main>

      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <p>© 2026 AutoTriage AI Assistant • Aqlior Associate AI Engineer Take-Home Assessment</p>
          <div className="flex items-center space-x-3 text-slate-400">
            <span>FastAPI Backend</span>
            <span>•</span>
            <span>React TypeScript</span>
            <span>•</span>
            <span>ChromaDB Vector RAG</span>
            <span>•</span>
            <span>PostgreSQL Persistence</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
