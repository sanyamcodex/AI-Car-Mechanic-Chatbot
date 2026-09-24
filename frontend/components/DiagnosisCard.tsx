'use client';

import React from 'react';
import { DiagnosisInfo } from '../lib/types';

interface DiagnosisCardProps {
  diagnosis: DiagnosisInfo;
  onBook?: () => void;
}

export const DiagnosisCard: React.FC<DiagnosisCardProps> = ({ diagnosis, onBook }) => {
  const topLabel =
    diagnosis.top_cause_label ||
    diagnosis.top?.cause_key?.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) ||
    'Mechanical Fault';

  const confidencePct = Math.round(
    (diagnosis.confidence || diagnosis.top?.confidence || 0.85) * 100
  );

  const service = diagnosis.service;

  return (
    <div className="bg-slate-900/90 border-2 border-orange-500/80 rounded-2xl p-4 sm:p-5 my-3 shadow-xl backdrop-blur-sm max-w-lg">
      {/* Header with confidence badge */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-orange-400">
            Diagnosis Result
          </span>
          <h3 className="text-lg font-bold text-white mt-0.5">{topLabel}</h3>
        </div>
        <div className="flex items-center gap-1.5 bg-orange-950/70 border border-orange-600/50 text-orange-300 px-2.5 py-1 rounded-full text-xs font-bold">
          <span>{confidencePct}%</span>
          <span className="text-[10px] font-normal text-orange-400">confidence</span>
        </div>
      </div>

      {/* Safety Alert if applicable */}
      {diagnosis.safety_alert && (
        <div className="flex items-center gap-2 bg-red-950/60 border border-red-700/60 rounded-xl p-2.5 mb-3 text-xs text-red-200">
          <span className="text-base">⚠️</span>
          <p className="font-semibold">{diagnosis.safety_alert}</p>
        </div>
      )}

      {/* Estimated Service & Pricing */}
      {service && (
        <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3 mb-4 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Recommended Service:</span>
            <span className="font-semibold text-slate-100">{service.name}</span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Estimated Cost:</span>
            <span className="font-bold text-emerald-400">
              ₹{service.price_min.toLocaleString()} – ₹{service.price_max.toLocaleString()}
            </span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Estimated Duration:</span>
            <span className="text-slate-200">~{service.duration_hours} hours</span>
          </div>
        </div>
      )}

      {/* Ranked alternatives */}
      {diagnosis.ranked && diagnosis.ranked.length > 1 && (
        <div className="mb-4">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
            Other possibilities:
          </span>
          <ul className="mt-1 space-y-1 text-xs text-slate-300">
            {diagnosis.ranked.slice(1, 3).map((r, idx) => (
              <li key={idx} className="flex justify-between items-center text-slate-400">
                <span>{r.cause_key.replace(/_/g, ' ')}</span>
                <span className="font-mono text-slate-500">{Math.round(r.confidence * 100)}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Call to action */}
      {onBook && (
        <button
          type="button"
          onClick={onBook}
          className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white font-bold text-sm shadow-lg shadow-orange-500/20 transition-all flex items-center justify-center gap-2 group cursor-pointer"
        >
          <span>Book Certified Mechanic</span>
          <svg
            className="w-4 h-4 transition-transform group-hover:translate-x-1"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      )}
    </div>
  );
};
