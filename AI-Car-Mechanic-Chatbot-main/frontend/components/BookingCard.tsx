'use client';

import React from 'react';
import Link from 'next/link';
import { BookingInfo } from '../lib/types';

interface BookingCardProps {
  booking: BookingInfo | Record<string, any>;
}

export const BookingCard: React.FC<BookingCardProps> = ({ booking }) => {
  const serviceName = booking.service?.name || booking.service || 'Diagnostic Service';
  const mechanicName = booking.mechanic?.name || booking.mechanic || 'Assigned Certified Specialist';
  const scheduledAt = booking.scheduled_at || 'Confirmed Slot';
  const bookingId = booking.id || 'BK-PENDING';

  return (
    <div className="bg-slate-900 border-2 border-emerald-500/80 rounded-2xl p-4 sm:p-5 my-3 shadow-xl max-w-lg">
      <div className="flex items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-xl">✅</span>
          <div>
            <h4 className="font-bold text-white text-base">Booking Confirmed</h4>
            <span className="text-[11px] font-mono text-emerald-400">ID: {bookingId}</span>
          </div>
        </div>
        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-700/50">
          CONFIRMED
        </span>
      </div>

      <div className="py-3 space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-slate-400">Service:</span>
          <span className="font-semibold text-slate-100 text-right">{serviceName}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Mechanic:</span>
          <span className="font-semibold text-slate-100 text-right">{mechanicName}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Time:</span>
          <span className="font-semibold text-emerald-400 text-right">{scheduledAt}</span>
        </div>
        {booking.city && (
          <div className="flex justify-between">
            <span className="text-slate-400">Location:</span>
            <span className="text-slate-200 text-right">{booking.city}</span>
          </div>
        )}
      </div>

      <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
        <p className="text-slate-400 text-[11px]">
          Mechanic will call 15 minutes before arrival.
        </p>
        {bookingId !== 'BK-PENDING' && (
          <Link
            href={`/booking/${bookingId}`}
            className="text-orange-400 hover:text-orange-300 font-bold hover:underline inline-flex items-center gap-1"
          >
            <span>View Receipt</span>
            <span>&rarr;</span>
          </Link>
        )}
      </div>
    </div>
  );
};
