import axios from 'axios';
import { Ticket, TicketCreatePayload, TicketUpdatePayload, TicketListResponse } from '../types/ticket';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 45000, // 45 seconds to accommodate local LLM inference if needed
});

export const ticketsApi = {
  /**
   * Submit a new ticket, triggering synchronous LLM Triage + RAG Draft
   */
  async createTicket(payload: TicketCreatePayload): Promise<Ticket> {
    const response = await apiClient.post<Ticket>('/tickets', payload);
    return response.data;
  },

  /**
   * Fetch tickets with optional filters and search
   */
  async getTickets(params?: {
    status?: string;
    category?: string;
    priority?: string;
    search?: string;
    page?: number;
    limit?: number;
  }): Promise<TicketListResponse> {
    const response = await apiClient.get<TicketListResponse>('/tickets', { params });
    return response.data;
  },

  /**
   * Fetch single ticket details by ID
   */
  async getTicket(id: number): Promise<Ticket> {
    const response = await apiClient.get<Ticket>(`/tickets/${id}`);
    return response.data;
  },

  /**
   * Update ticket status, draft reply, notes, or triage labels
   */
  async updateTicket(id: number, payload: TicketUpdatePayload): Promise<Ticket> {
    const response = await apiClient.patch<Ticket>(`/tickets/${id}`, payload);
    return response.data;
  },

  /**
   * Stream draft reply token-by-token using SSE
   */
  streamDraft(
    ticketId: number,
    onToken: (token: string) => void,
    onComplete: (fullDraft: string, citations: string[]) => void,
    onError: (err: any) => void
  ): () => void {
    const url = `${API_BASE}/tickets/${ticketId}/stream-draft`;
    const eventSource = new EventSource(url);
    let accumulated = '';
    let citations: string[] = [];

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.citations && data.citations.length > 0) {
          citations = data.citations;
        }
        if (data.token) {
          accumulated += data.token;
          onToken(data.token);
        }
        if (data.done) {
          eventSource.close();
          onComplete(accumulated, citations);
        }
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    };

    eventSource.onerror = (err) => {
      eventSource.close();
      onError(err);
    };

    return () => {
      eventSource.close();
    };
  },
};
