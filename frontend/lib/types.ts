export interface SuggestedReply {
  id: string;
  label: string;
  question_id: string;
}

export interface AttachmentItem {
  id: string;
  kind: 'image' | 'audio' | 'video';
  original_name: string;
  mime_type?: string;
  file_url: string;
  url?: string;
}

export interface UploadAttachmentDraft {
  localId: string;
  file: File;
  kind: 'image' | 'audio' | 'video';
  previewUrl: string;
  progress: number;
  uploadedId?: string;
  error?: string;
}

export interface ServiceInfo {
  key: string;
  name: string;
  description?: string;
  price_min: number;
  price_max: number;
  duration_hours: number;
  currency?: string;
}

export interface RankedCause {
  cause_key: string;
  label?: string;
  confidence: number;
  why?: string[];
}

export interface DiagnosisInfo {
  id?: string;
  top_cause_key?: string;
  top_cause_label?: string;
  confidence?: number;
  severity?: number | string;
  safety_alert?: string | null;
  ranked?: RankedCause[];
  service?: ServiceInfo;
  top?: {
    cause_key: string;
    label?: string;
    description?: string;
    confidence: number;
  };
}

export interface MechanicInfo {
  id: number;
  name: string;
  city: string;
  phone?: string;
}

export interface BookingInfo {
  id: string;
  status: string;
  customer_name: string;
  phone: string;
  city: string;
  scheduled_at: string;
  service: ServiceInfo;
  mechanic: MechanicInfo | null;
  diagnosis_id?: string | null;
  conversation_id?: string | null;
  created_at?: string;
}

export interface Message {
  id: string;
  sender: 'user' | 'bot' | 'system';
  role?: 'user' | 'bot' | 'system';
  kind: 'text' | 'question' | 'diagnosis' | 'booking' | 'media';
  text: string;
  meta?: {
    attachments?: AttachmentItem[];
    diagnosis?: DiagnosisInfo;
    booking?: BookingInfo;
    suggested_replies?: SuggestedReply[];
    choice?: { question_id: string; option_id: string; label?: string };
    ai_used?: boolean;
  };
  client_msg_id?: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  title?: string;
  status?: string;
  state?: string;
  messages?: Message[];
  suggested_replies?: SuggestedReply[];
  diagnosis?: DiagnosisInfo | null;
  booking?: BookingInfo | null;
  cta?: { type: string; diagnosis_id: string } | null;
  created_at: string;
  updated_at: string;
}

export interface ChatResponse {
  conversation_id: string;
  state?: string;
  messages: Message[];
  suggested_replies: SuggestedReply[];
  diagnosis?: DiagnosisInfo | null;
  cta?: { type: string; diagnosis_id: string } | null;
  meta?: { ai_calls?: number };
}

export interface ApiErrorShape {
  error: {
    code: string;
    message: string;
    fields?: Record<string, string[]>;
    details?: Record<string, unknown>;
  };
}
