'use client';

import React from 'react';
import { UploadAttachmentDraft } from '../lib/types';

interface AttachmentPreviewProps {
  draft: UploadAttachmentDraft;
  onRemove: (localId: string) => void;
}

export const AttachmentPreview: React.FC<AttachmentPreviewProps> = ({ draft, onRemove }) => {
  const isImage = draft.kind === 'image';
  const isAudio = draft.kind === 'audio';
  const isVideo = draft.kind === 'video';

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="relative group flex items-center gap-2.5 bg-slate-900 border border-slate-700/80 rounded-xl p-2 pr-3 max-w-xs shadow-md">
      {/* Thumbnail or Media Icon */}
      <div className="relative w-11 h-11 rounded-lg overflow-hidden bg-slate-800 flex-shrink-0 flex items-center justify-center">
        {isImage && draft.previewUrl ? (
          <img
            src={draft.previewUrl}
            alt={draft.file.name}
            className="w-full h-full object-cover"
          />
        ) : isAudio ? (
          <span className="text-xl" role="img" aria-label="Audio">
            🎙️
          </span>
        ) : (
          <span className="text-xl" role="img" aria-label="Video">
            📹
          </span>
        )}

        {/* Progress overlay */}
        {draft.progress < 100 && !draft.error && (
          <div className="absolute inset-0 bg-slate-950/70 flex items-center justify-center">
            <span className="text-[10px] font-bold text-orange-400">{draft.progress}%</span>
          </div>
        )}
      </div>

      {/* Info & Progress Bar */}
      <div className="flex-1 min-w-0 flex flex-col justify-center">
        <p className="text-xs font-medium text-slate-200 truncate">{draft.file.name}</p>
        <span className="text-[11px] text-slate-400">{formatFileSize(draft.file.size)}</span>

        {/* Progress indicator */}
        {draft.progress < 100 && !draft.error && (
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-1 overflow-hidden">
            <div
              className="bg-orange-500 h-full transition-all duration-150 ease-out"
              style={{ width: `${draft.progress}%` }}
            />
          </div>
        )}

        {/* Error text */}
        {draft.error && (
          <span className="text-[11px] text-red-400 font-medium truncate mt-0.5">
            {draft.error}
          </span>
        )}
      </div>

      {/* Remove Button */}
      <button
        type="button"
        onClick={() => onRemove(draft.localId)}
        aria-label="Remove attachment"
        className="text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 w-6 h-6 rounded-full flex items-center justify-center transition-colors flex-shrink-0"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-3.5 w-3.5"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>
    </div>
  );
};
