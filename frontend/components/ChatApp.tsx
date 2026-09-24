'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Message, SuggestedReply, DiagnosisInfo, BookingInfo, Conversation } from '../lib/types';
import { sendChat, getConversation, getConversations } from '../lib/api';
import { MessageBubble } from './MessageBubble';
import { Composer } from './Composer';
import { BookingModal } from './BookingModal';

interface ChatAppProps {
  initialConversationId?: string | null;
}

const DEFAULT_STARTER_REPLIES: SuggestedReply[] = [
  { id: 'engine_no_crank', label: "🚗 Car won't start", question_id: 'intake' },
  { id: 'brake_squeal', label: '🛑 Brake noise', question_id: 'intake' },
  { id: 'overheating', label: '🌡️ Overheating', question_id: 'intake' },
  { id: 'check_engine_light', label: '⚠️ Warning light on', question_id: 'intake' },
  { id: 'vibration_speed', label: '〰️ Vibration / shaking', question_id: 'intake' },
  { id: 'ac_not_cooling', label: '❄️ AC not cooling', question_id: 'intake' },
];

export const ChatApp: React.FC<ChatAppProps> = ({ initialConversationId }) => {
  const [conversationId, setConversationId] = useState<string | null>(initialConversationId || null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [suggestedReplies, setSuggestedReplies] = useState<SuggestedReply[]>(DEFAULT_STARTER_REPLIES);
  const [activeDiagnosis, setActiveDiagnosis] = useState<DiagnosisInfo | null>(null);
  const [isBookingModalOpen, setIsBookingModalOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [historyList, setHistoryList] = useState<Conversation[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, suggestedReplies, isProcessing]);

  useEffect(() => {
    if (conversationId) {
      loadHistory(conversationId);
      saveConversationIdToStorage(conversationId);
    } else {
      setMessages([
        {
          id: 'welcome',
          sender: 'bot',
          kind: 'text',
          text: "Hello! I'm your virtual mechanic assistant. What seems to be the problem with your vehicle? Describe your symptoms, upload engine audio or photos, or pick one of the common issues below.",
          created_at: new Date().toISOString(),
        },
      ]);
      setSuggestedReplies(DEFAULT_STARTER_REPLIES);
      setActiveDiagnosis(null);
    }
  }, [conversationId]);

  const saveConversationIdToStorage = (id: string) => {
    try {
      const stored = JSON.parse(localStorage.getItem('car_mechanic_conv_ids') || '[]');
      if (!stored.includes(id)) {
        stored.unshift(id);
        localStorage.setItem('car_mechanic_conv_ids', JSON.stringify(stored.slice(0, 20)));
      }
    } catch {
      // ignore
    }
  };

  const getStoredConversationIds = (): string[] => {
    try {
      return JSON.parse(localStorage.getItem('car_mechanic_conv_ids') || '[]');
    } catch {
      return [];
    }
  };

  const loadHistory = async (id: string) => {
    try {
      const conv = await getConversation(id);
      if (conv.messages) {
        setMessages(conv.messages);

        for (const msg of conv.messages) {
          if (msg.meta?.diagnosis) {
            setActiveDiagnosis(msg.meta.diagnosis);
          }
        }

        const lastBot = [...conv.messages].reverse().find((m) => m.sender === 'bot');
        if (lastBot?.meta?.suggested_replies) {
          setSuggestedReplies(lastBot.meta.suggested_replies);
        } else if (conv.suggested_replies) {
          setSuggestedReplies(conv.suggested_replies);
        }
      }
    } catch (err) {
      console.error('Failed to load conversation history:', err);
    }
  };

  const openHistoryDrawer = async () => {
    setIsHistoryOpen(true);
    setLoadingHistory(true);
    try {
      const ids = getStoredConversationIds();
      const convs = await getConversations(ids.length > 0 ? ids : undefined);
      setHistoryList(convs);
    } catch (err) {
      console.error('Failed to load history list:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const startNewChat = () => {
    setConversationId(null);
    setActiveDiagnosis(null);
    setMessages([
      {
        id: 'welcome-' + Date.now(),
        sender: 'bot',
        kind: 'text',
        text: "Hello! I'm your virtual mechanic assistant. What seems to be the problem with your vehicle? Describe your symptoms, upload engine audio or photos, or pick one of the common issues below.",
        created_at: new Date().toISOString(),
      },
    ]);
    setSuggestedReplies(DEFAULT_STARTER_REPLIES);
  };

  const handleSendTurn = async (
    text?: string,
    choice?: { question_id: string; option_id: string; label?: string } | null,
    uploadIds?: string[]
  ) => {
    if (isProcessing) return;

    const userMsgText = text || choice?.label || choice?.option_id || '';
    const tempUserMsgId = 'usr-' + Date.now();
    const clientMsgId = 'cm-' + Math.random().toString(36).substring(2, 10);

    const userMessage: Message = {
      id: tempUserMsgId,
      sender: 'user',
      text: userMsgText,
      kind: 'text',
      meta: choice ? { choice } : {},
      client_msg_id: clientMsgId,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setSuggestedReplies([]);
    setIsProcessing(true);

    try {
      const res = await sendChat({
        conversation_id: conversationId,
        client_msg_id: clientMsgId,
        text,
        choice,
        upload_ids: uploadIds && uploadIds.length > 0 ? uploadIds : undefined,
      });

      if (!conversationId && res.conversation_id) {
        setConversationId(res.conversation_id);
        saveConversationIdToStorage(res.conversation_id);
      }

      if (res.diagnosis) {
        setActiveDiagnosis(res.diagnosis);
      }

      setMessages((prev) => [...prev, ...(res.messages || [])]);
      setSuggestedReplies(res.suggested_replies || []);
    } catch (err: any) {
      console.error('Chat error:', err);
      setMessages((prev) => [
        ...prev,
        {
          id: 'err-' + Date.now(),
          sender: 'bot',
          kind: 'text',
          text: "I'm having trouble processing your request right now. Please try again or rephrase.",
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleBookingSuccess = (booking: BookingInfo) => {
    const bookingMessage: Message = {
      id: 'book-' + Date.now(),
      sender: 'bot',
      kind: 'booking',
      text: `Your mechanic appointment has been confirmed (Booking ID: ${booking.id}). Our certified specialist will call you before heading over.`,
      meta: {
        booking,
      },
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, bookingMessage]);
    setSuggestedReplies(DEFAULT_STARTER_REPLIES);
  };

  return (
    <div className="flex flex-col h-full w-full bg-slate-950 text-slate-100 overflow-hidden relative">
      {/* Header */}
      <header className="flex items-center justify-between px-4 sm:px-6 py-3.5 bg-slate-900 border-b border-slate-800 z-10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-orange-500/15 border border-orange-500/30 flex items-center justify-center text-lg">
            🔧
          </div>
          <div>
            <h1 className="font-bold text-sm sm:text-base text-white">Car Mechanic Assistant</h1>
            <p className="text-[11px] text-slate-400">Senior Virtual Diagnostic &amp; Booking Engine</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={openHistoryDrawer}
            className="px-3 py-1.5 rounded-xl text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <span>📜</span>
            <span className="hidden sm:inline">History</span>
          </button>

          <button
            type="button"
            onClick={startNewChat}
            className="px-3 py-1.5 rounded-xl text-xs font-medium text-white bg-orange-600 hover:bg-orange-500 transition-colors flex items-center gap-1.5 cursor-pointer shadow-sm"
          >
            <span>➕</span>
            <span className="hidden sm:inline">New Chat</span>
          </button>
        </div>
      </header>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onBookDiagnosis={() => setIsBookingModalOpen(true)}
          />
        ))}

        {isProcessing && (
          <div className="flex items-center gap-2 self-start p-3 bg-slate-900/80 border border-slate-800 rounded-2xl rounded-tl-none w-fit">
            <span className="w-2 h-2 rounded-full bg-orange-400 animate-bounce" />
            <span className="w-2 h-2 rounded-full bg-orange-400 animate-bounce [animation-delay:0.2s]" />
            <span className="w-2 h-2 rounded-full bg-orange-400 animate-bounce [animation-delay:0.4s]" />
          </div>
        )}

        {!isProcessing && suggestedReplies.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-2 pb-1">
            {suggestedReplies.map((reply, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  if (reply.question_id === 'book_offer' && reply.id === 'yes') {
                    setIsBookingModalOpen(true);
                  } else {
                    handleSendTurn(undefined, {
                      question_id: reply.question_id,
                      option_id: reply.id,
                      label: reply.label,
                    });
                  }
                }}
                className="px-3.5 py-1.5 rounded-full text-xs font-medium bg-slate-800 hover:bg-orange-500 hover:text-white text-slate-200 border border-slate-700 hover:border-orange-500 transition-all shadow-sm active:scale-95 cursor-pointer"
              >
                {reply.label}
              </button>
            ))}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Composer Input Area */}
      <Composer
        onSendMessage={(txt, uploadIds) => handleSendTurn(txt, null, uploadIds)}
        disabled={isProcessing}
      />

      {/* Booking Modal */}
      <BookingModal
        isOpen={isBookingModalOpen}
        onClose={() => setIsBookingModalOpen(false)}
        diagnosis={activeDiagnosis}
        conversationId={conversationId}
        onSuccess={handleBookingSuccess}
      />

      {/* History Drawer Modal */}
      {isHistoryOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md p-5 shadow-2xl relative max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <span>📜</span> Diagnostic History
              </h2>
              <button
                type="button"
                onClick={() => setIsHistoryOpen(false)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2">
              {loadingHistory ? (
                <div className="p-6 text-center text-xs text-slate-400">Loading sessions...</div>
              ) : historyList.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-400">
                  No previous sessions found. Start a new diagnosis!
                </div>
              ) : (
                historyList.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => {
                      setConversationId(c.id);
                      setIsHistoryOpen(false);
                    }}
                    className={`w-full text-left p-3 rounded-xl border transition-all cursor-pointer ${
                      c.id === conversationId
                        ? 'bg-orange-950/40 border-orange-500 text-white'
                        : 'bg-slate-800/70 border-slate-700/60 hover:bg-slate-800 text-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <h4 className="font-semibold text-xs truncate max-w-[220px]">
                        {c.title || 'Diagnostic Session'}
                      </h4>
                      <span className="text-[10px] font-mono text-slate-400 uppercase">
                        {c.status}
                      </span>
                    </div>
                    <div className="flex items-center justify-between mt-1 text-[11px] text-slate-400">
                      <span>{c.messages ? `${c.messages.length} messages` : 'Session active'}</span>
                      <span>
                        {new Date(c.updated_at || c.created_at).toLocaleDateString(undefined, {
                          month: 'short',
                          day: 'numeric',
                        })}
                      </span>
                    </div>
                  </button>
                ))
              )}
            </div>

            <div className="pt-3 border-t border-slate-800 mt-2 flex justify-end">
              <button
                type="button"
                onClick={() => setIsHistoryOpen(false)}
                className="px-4 py-1.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
