export interface EntitiesMap {
  [key: string]: string | null | undefined;
}

export interface Ticket {
  id: number;
  title: string;
  description: string;
  customer_email?: string | null;
  status: 'open' | 'in_progress' | 'resolved' | 'closed' | string;
  category?: string | null;
  priority?: 'low' | 'medium' | 'high' | 'urgent' | string | null;
  sentiment?: 'positive' | 'neutral' | 'negative' | 'frustrated' | string | null;
  summary?: string | null;
  entities: EntitiesMap;
  draft_reply?: string | null;
  cited_articles: string[];
  agent_notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TicketCreatePayload {
  title: string;
  description: string;
  customer_email?: string;
}

export interface TicketUpdatePayload {
  status?: string;
  category?: string;
  priority?: string;
  draft_reply?: string;
  agent_notes?: string;
}

export interface TicketListResponse {
  total: number;
  tickets: Ticket[];
}
