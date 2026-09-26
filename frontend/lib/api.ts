import {
  ApiErrorShape,
  BookingInfo,
  ChatResponse,
  Conversation,
} from './types';
import { API_TIMEOUT_MS, CHAT_TIMEOUT_MS } from './constants';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  code: string;
  fields?: Record<string, string[]>;
  details?: Record<string, unknown>;

  constructor(
    status: number,
    code: string,
    message: string,
    fields?: Record<string, string[]>,
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.fields = fields;
    this.details = details;
  }
}

async function parseResponse<T>(res: Response): Promise<T> {
  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }
  }

  if (!res.ok) {
    const err = data as ApiErrorShape | null;
    if (err && err.error) {
      throw new ApiError(
        res.status,
        err.error.code,
        err.error.message,
        err.error.fields,
        err.error.details
      );
    }
    throw new ApiError(res.status, 'server_error', `Request failed (${res.status})`);
  }

  return data as T;
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs: number = API_TIMEOUT_MS
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(options.headers || {}),
      },
    });
    return parseResponse<T>(res);
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(408, 'timeout', 'Request timed out. The server may be waking up.');
    }
    throw new ApiError(0, 'network_error', 'Network error. Check your connection or API URL.');
  } finally {
    clearTimeout(timer);
  }
}

export async function checkHealth(): Promise<{ status: string; db: boolean }> {
  return apiFetch('/api/health/', { method: 'GET' }, 10000);
}

export interface SendChatPayload {
  conversation_id?: string | null;
  client_msg_id?: string;
  text?: string;
  message?: string;
  choice?: { question_id: string; option_id: string; label?: string } | null;
  upload_ids?: string[];
}

export async function sendChat(payload: SendChatPayload): Promise<ChatResponse> {
  const body: Record<string, unknown> = {
    conversation_id: payload.conversation_id || undefined,
    client_msg_id: payload.client_msg_id,
    upload_ids: payload.upload_ids,
    choice: payload.choice || undefined,
  };
  const msg = payload.text || payload.message;
  if (msg) {
    body.message = msg;
    body.text = msg;
  }

  return apiFetch<ChatResponse>(
    '/api/chat/',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    CHAT_TIMEOUT_MS
  );
}

export async function getConversation(id: string): Promise<Conversation> {
  return apiFetch<Conversation>(`/api/conversations/${id}/`, { method: 'GET' });
}

export async function getConversations(ids?: string[]): Promise<Conversation[]> {
  const query = ids && ids.length > 0 ? `?ids=${ids.join(',')}` : '';
  return apiFetch<Conversation[]>(`/api/conversations/${query}`, { method: 'GET' });
}

export interface UploadResult {
  id: string;
  conversation_id?: string;
  kind: string;
  mime?: string;
  mime_type?: string;
  size?: number;
  url?: string;
  file_url?: string;
  status?: string;
  analysis_status?: string;
}

export function uploadFile(
  file: File,
  onProgress?: (percent: number) => void,
  conversationId?: string | null
): Promise<UploadResult> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append('file', file);
    if (conversationId) {
      formData.append('conversation_id', conversationId);
    }

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener('load', () => {
      try {
        const data = JSON.parse(xhr.responseText || '{}');
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(data as UploadResult);
          return;
        }
        if (data.error) {
          reject(
            new ApiError(
              xhr.status,
              data.error.code,
              data.error.message,
              data.error.fields,
              data.error.details
            )
          );
          return;
        }
        reject(new ApiError(xhr.status, 'upload_failed', 'Upload failed'));
      } catch {
        reject(new ApiError(xhr.status, 'parse_error', 'Invalid upload response'));
      }
    });

    xhr.addEventListener('error', () => {
      reject(new ApiError(0, 'network_error', 'Upload network error'));
    });

    xhr.open('POST', `${API_URL}/api/upload/`);
    xhr.send(formData);
  });
}

export interface CreateBookingPayload {
  customer_name: string;
  phone: string;
  city: string;
  scheduled_at: string;
  service_key?: string | null;
  conversation_id?: string | null;
  diagnosis_id?: string | null;
  idempotency_key?: string;
  notes?: string;
}

export async function createBooking(
  payload: CreateBookingPayload,
  idempotencyKey?: string
): Promise<BookingInfo> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }

  return apiFetch<BookingInfo>(
    '/api/booking/',
    {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    },
    API_TIMEOUT_MS
  );
}

export async function getBooking(id: string): Promise<BookingInfo> {
  return apiFetch<BookingInfo>(`/api/booking/${id}/`, { method: 'GET' });
}
