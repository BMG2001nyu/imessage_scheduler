const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002";

export interface Message {
  id: string;
  phone_number: string;
  body: string;
  scheduled_at: string;
  timezone: string;
  status: string;
  created_at: string;
  updated_at: string;
  accepted_at: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  failed_at: string | null;
  failure_reason: string | null;
  attempts: number;
  max_attempts: number;
  gateway_message_id: string | null;
}

export interface MessageListResponse {
  messages: Message[];
  total: number;
}

export interface Stats {
  queued: number;
  accepted: number;
  sent: number;
  delivered: number;
  failed: number;
  cancelled: number;
  total: number;
}

export interface CreateMessagePayload {
  phone_number: string;
  body: string;
  scheduled_at: string;
  timezone: string;
}

export interface UpdateMessagePayload {
  phone_number?: string;
  body?: string;
  scheduled_at?: string;
  timezone?: string;
}

class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  createMessage: (data: CreateMessagePayload) =>
    request<Message>("/api/messages", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listMessages: (params?: { status?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));
    const qs = query.toString();
    return request<MessageListResponse>(`/api/messages${qs ? `?${qs}` : ""}`);
  },

  getMessage: (id: string) => request<Message>(`/api/messages/${id}`),

  updateMessage: (id: string, data: UpdateMessagePayload) =>
    request<Message>(`/api/messages/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  cancelMessage: (id: string) =>
    request<Message>(`/api/messages/${id}`, { method: "DELETE" }),

  getStats: () => request<Stats>("/api/stats"),

  healthCheck: () => request<{ status: string }>("/api/health"),
};
