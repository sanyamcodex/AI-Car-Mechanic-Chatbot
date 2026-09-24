'use client';

import React, { useState, useRef } from 'react';
import { UploadAttachmentDraft } from '../lib/types';
import { uploadFile } from '../lib/api';
import { AttachmentPreview } from './AttachmentPreview';
import { Recorder } from './Recorder';

interface ComposerProps {
  onSendMessage: (text: string, uploadIds: string[]) => void;
  disabled?: boolean;
}

const MAX_IMAGE_SIZE = 5 * 1024 * 1024;
const MAX_AUDIO_SIZE = 10 * 1024 * 1024;
const MAX_VIDEO_SIZE = 25 * 1024 * 1024;

export const Composer: React.FC<ComposerProps> = ({ onSendMessage, disabled = false }) => {
  const [text, setText] = useState('');
  const [drafts, setDrafts] = useState<UploadAttachmentDraft[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const determineKind = (file: File): 'image' | 'audio' | 'video' | null => {
    if (file.type.startsWith('image/')) return 'image';
    if (file.type.startsWith('audio/')) return 'audio';
    if (file.type.startsWith('video/')) return 'video';
    return null;
  };

  const validateFile = (file: File, kind: 'image' | 'audio' | 'video'): string | null => {
    if (kind === 'image' && file.size > MAX_IMAGE_SIZE) {
      return `Image is too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Max 5MB.`;
    }
    if (kind === 'audio' && file.size > MAX_AUDIO_SIZE) {
      return `Audio is too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Max 10MB.`;
    }
    if (kind === 'video' && file.size > MAX_VIDEO_SIZE) {
      return `Video is too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Max 25MB.`;
    }
    return null;
  };

  const handleProcessFile = async (file: File) => {
    setGeneralError(null);
    const kind = determineKind(file);
    if (!kind) {
      setGeneralError(`Unsupported file format (${file.type || 'unknown'}).`);
      return;
    }

    const validationError = validateFile(file, kind);
    if (validationError) {
      setGeneralError(validationError);
      return;
    }

    const localId = 'draft-' + Math.random().toString(36).substring(2, 9);
    const previewUrl = kind === 'image' ? URL.createObjectURL(file) : '';

    const newDraft: UploadAttachmentDraft = {
      localId,
      file,
      kind,
      previewUrl,
      progress: 0,
    };

    setDrafts((prev) => [...prev, newDraft]);

    try {
      const uploadedItem = await uploadFile(file, (percent) => {
        setDrafts((prev) =>
          prev.map((d) => (d.localId === localId ? { ...d, progress: percent } : d))
        );
      });

      setDrafts((prev) =>
        prev.map((d) =>
          d.localId === localId
            ? { ...d, progress: 100, uploadedId: uploadedItem.id }
            : d
        )
      );
    } catch (err: any) {
      setDrafts((prev) =>
        prev.map((d) =>
          d.localId === localId
            ? { ...d, error: err.message || 'Upload failed' }
            : d
        )
      );
    }
  };

  const handleFilesSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    Array.from(e.target.files).forEach((file) => handleProcessFile(file));
    e.target.value = '';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files) {
      Array.from(e.dataTransfer.files).forEach((file) => handleProcessFile(file));
    }
  };

  const handleRemoveDraft = (localId: string) => {
    setDrafts((prev) => {
      const removed = prev.find((d) => d.localId === localId);
      if (removed?.previewUrl) {
        URL.revokeObjectURL(removed.previewUrl);
      }
      return prev.filter((d) => d.localId !== localId);
    });
  };

  const isUploading = drafts.some((d) => d.progress < 100 && !d.error);

  const handleSend = () => {
    if (disabled || isUploading) return;
    const trimmed = text.trim();
    const readyUploadIds = drafts
      .filter((d) => d.uploadedId && !d.error)
      .map((d) => d.uploadedId as string);

    if (!trimmed && readyUploadIds.length === 0) return;

    onSendMessage(trimmed, readyUploadIds);
    setText('');
    setDrafts([]);
    setGeneralError(null);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      className={`border-t bg-slate-900/95 backdrop-blur px-3 sm:px-4 py-3 transition-colors ${
        isDragOver ? 'border-orange-500 bg-orange-950/20' : 'border-slate-800'
      }`}
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFilesSelected}
        multiple
        accept="image/*,audio/*,video/*"
        className="hidden"
      />

      {/* Error Banner */}
      {generalError && (
        <div className="flex items-center justify-between text-xs text-red-300 bg-red-950/80 border border-red-800 rounded-xl px-3 py-1.5 mb-2">
          <span>⚠️ {generalError}</span>
          <button
            type="button"
            onClick={() => setGeneralError(null)}
            className="text-red-400 hover:text-white font-bold ml-2"
          >
            &times;
          </button>
        </div>
      )}

      {/* Previews Area */}
      {drafts.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2.5 max-h-36 overflow-y-auto">
          {drafts.map((d) => (
            <AttachmentPreview key={d.localId} draft={d} onRemove={handleRemoveDraft} />
          ))}
        </div>
      )}

      {/* Audio Recorder Mode */}
      {isRecording ? (
        <Recorder
          onRecorded={(file) => {
            setIsRecording(false);
            handleProcessFile(file);
          }}
          onCancel={() => setIsRecording(false)}
        />
      ) : (
        /* Composer Input Box */
        <div className="flex items-end gap-2 bg-slate-800/80 border border-slate-700/80 rounded-2xl p-1.5 focus-within:border-orange-500 transition-colors shadow-inner">
          {/* File Attach Button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            aria-label="Attach file"
            className="text-slate-400 hover:text-orange-400 p-2 rounded-xl hover:bg-slate-700/50 transition-colors flex-shrink-0 cursor-pointer disabled:opacity-40"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
              />
            </svg>
          </button>

          {/* Record Audio Button */}
          <button
            type="button"
            onClick={() => setIsRecording(true)}
            disabled={disabled}
            aria-label="Record audio"
            className="text-slate-400 hover:text-red-400 p-2 rounded-xl hover:bg-slate-700/50 transition-colors flex-shrink-0 cursor-pointer disabled:opacity-40"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>
          </button>

          {/* Text Input Area */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={
              isDragOver
                ? 'Drop media here...'
                : 'Describe symptom or noise (e.g. brakes grinding when coming to a stop)...'
            }
            className="flex-1 bg-transparent text-sm text-slate-100 placeholder-slate-400 outline-none resize-none py-2 px-1 max-h-32 min-h-[38px]"
          />

          {/* Send Button */}
          <button
            type="button"
            onClick={handleSend}
            disabled={disabled || isUploading || (!text.trim() && drafts.length === 0)}
            className="bg-orange-500 hover:bg-orange-600 disabled:opacity-30 disabled:hover:bg-orange-500 text-white font-bold p-2 sm:px-4 sm:py-2 rounded-xl text-xs transition-colors flex items-center justify-center gap-1.5 flex-shrink-0 cursor-pointer"
          >
            <span className="hidden sm:inline">Send</span>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
};
