'use client';

import React, { useState } from 'react';
import { Message, AttachmentItem } from '../lib/types';
import { DiagnosisCard } from './DiagnosisCard';
import { BookingCard } from './BookingCard';

interface MessageBubbleProps {
  message: Message;
  onBookDiagnosis?: () => void;
}

const AttachmentView: React.FC<{ item: AttachmentItem }> = ({ item }) => {
  const [hasError, setHasError] = useState(false);

  if (hasError) {
    return (
      <div className="flex items-center gap-2 bg-slate-900 border border-slate-700/80 rounded-xl p-3 text-xs text-slate-400">
        <span>⚠️</span>
        <span>Media expired or unavailable</span>
      </div>
    );
  }

  if (item.kind === 'image') {
    return (
      <div className="rounded-xl overflow-hidden border border-slate-700/80 max-w-xs my-1 bg-slate-950">
        <img
          src={item.file_url}
          alt={item.original_name}
          onError={() => setHasError(true)}
          className="w-full h-auto max-h-64 object-cover"
        />
        <div className="p-1.5 text-[11px] text-slate-400 truncate">{item.original_name}</div>
      </div>
    );
  }

  if (item.kind === 'audio') {
    return (
      <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-2.5 max-w-xs my-1">
        <div className="text-[11px] text-slate-300 font-medium truncate mb-1">
          🎙️ {item.original_name}
        </div>
        <audio
          controls
          src={item.file_url}
          onError={() => setHasError(true)}
          className="w-full h-8"
        />
      </div>
    );
  }

  if (item.kind === 'video') {
    return (
      <div className="rounded-xl overflow-hidden border border-slate-700/80 max-w-xs my-1 bg-slate-950">
        <video
          controls
          src={item.file_url}
          onError={() => setHasError(true)}
          className="w-full max-h-64"
        />
        <div className="p-1.5 text-[11px] text-slate-400 truncate">{item.original_name}</div>
      </div>
    );
  }

  return null;
};

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onBookDiagnosis }) => {
  const isUser = message.sender === 'user';
  const meta = message.meta || {};
  const attachments = meta.attachments || [];
  const diagnosis = meta.diagnosis;
  const booking = meta.booking;

  const renderFormattedText = (rawText: string) => {
    // Format bold **text**
    const parts = rawText.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="font-bold text-white">{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  return (
    <div className={`flex flex-col gap-1.5 max-w-[85%] sm:max-w-[75%] ${isUser ? 'self-end items-end' : 'self-start items-start'}`}>
      {/* Attachments if any */}
      {attachments.length > 0 && (
        <div className="flex flex-col gap-1.5 mb-1">
          {attachments.map((att, idx) => (
            <AttachmentView key={att.id || idx} item={att} />
          ))}
        </div>
      )}

      {/* Message Text Bubble */}
      {message.text && (
        <div
          className={`p-3.5 sm:p-4 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words shadow-sm ${
            isUser
              ? 'bg-orange-600 text-white rounded-tr-none'
              : 'bg-slate-800/90 text-slate-100 border border-slate-700/70 rounded-tl-none'
          }`}
        >
          {renderFormattedText(message.text)}
        </div>
      )}

      {/* Embedded Diagnosis Card if attached to message */}
      {diagnosis && (
        <DiagnosisCard diagnosis={diagnosis} onBook={onBookDiagnosis} />
      )}

      {/* Embedded Booking Card if attached to message */}
      {booking && <BookingCard booking={booking} />}
    </div>
  );
};
