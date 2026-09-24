'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { getBooking, ApiError } from '../../../lib/api';
import { BookingInfo } from '../../../lib/types';

export default function BookingDetailPage() {
  const params = useParams();
  const bookingId = params?.id as string;

  const [booking, setBooking] = useState<BookingInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (bookingId) {
      loadBooking(bookingId);
    }
  }, [bookingId]);

  const loadBooking = async (id: string) => {
    setLoading(true);
    setErrorStatus(null);
    setErrorMessage(null);
    try {
      const data = await getBooking(id);
      setBooking(data);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setErrorStatus(err.status);
        setErrorMessage(err.message);
      } else {
        setErrorStatus(500);
        setErrorMessage('Unable to load booking details.');
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex flex-col items-center justify-center p-4">
        <div className="w-10 h-10 border-4 border-orange-500/20 border-t-orange-500 rounded-full animate-spin mb-4" />
        <p className="text-sm text-slate-400">Loading appointment details...</p>
      </div>
    );
  }

  if (errorStatus === 404) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex flex-col items-center justify-center p-4 text-center">
        <div className="text-5xl mb-3">🔍</div>
        <h1 className="text-2xl font-bold mb-2">Booking Not Found</h1>
        <p className="text-sm text-slate-400 max-w-sm mb-6">
          We could not find an appointment matching ID <span className="font-mono text-white">{bookingId}</span>.
        </p>
        <Link
          href="/"
          className="px-5 py-2.5 rounded-xl bg-orange-500 hover:bg-orange-600 text-white font-semibold text-sm transition-colors"
        >
          Return to Mechanic Chat
        </Link>
      </div>
    );
  }

  if (errorStatus || !booking) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex flex-col items-center justify-center p-4 text-center">
        <div className="text-5xl mb-3">⚠️</div>
        <h1 className="text-2xl font-bold mb-2">Failed to Load Booking</h1>
        <p className="text-sm text-red-400 max-w-sm mb-6">
          {errorMessage || 'An error occurred while retrieving your appointment.'}
        </p>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => loadBooking(bookingId)}
            className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-sm transition-colors cursor-pointer"
          >
            Retry
          </button>
          <Link
            href="/"
            className="px-5 py-2.5 rounded-xl bg-orange-500 hover:bg-orange-600 text-white font-semibold text-sm transition-colors"
          >
            Go to Chat
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-8 flex flex-col items-center justify-center">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 pb-6 border-b border-slate-800">
          <div>
            <span className="text-[11px] font-bold text-orange-400 uppercase tracking-wider">
              Appointment Receipt
            </span>
            <h1 className="text-2xl font-bold text-white mt-1">Mechanic Visit Confirmed</h1>
            <p className="text-xs text-slate-400 font-mono mt-0.5">Booking ID: {booking.id}</p>
          </div>
          <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-950 text-emerald-400 border border-emerald-700/50">
            {booking.status.toUpperCase()}
          </span>
        </div>

        {/* Appointment Details */}
        <div className="py-6 space-y-4 text-sm border-b border-slate-800">
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Scheduled Time</span>
            <span className="font-semibold text-white text-right">
              {new Date(booking.scheduled_at).toLocaleDateString(undefined, {
                weekday: 'short',
                month: 'short',
                day: 'numeric',
                year: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
              })}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Assigned Mechanic</span>
            <span className="font-semibold text-white text-right">{booking.mechanic?.name}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Mechanic Contact</span>
            <span className="font-mono text-slate-200 text-right">
              {booking.mechanic?.phone || '+91 98123 45670'}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Service</span>
            <span className="font-semibold text-white text-right">{booking.service?.name}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Estimated Cost</span>
            <span className="font-bold text-emerald-400 text-right">
              ₹{booking.service?.price_min?.toLocaleString()} – ₹
              {booking.service?.price_max?.toLocaleString()}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Customer Name</span>
            <span className="text-slate-200 text-right">{booking.customer_name}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">Phone Number</span>
            <span className="font-mono text-slate-200 text-right">{booking.phone}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-400">City</span>
            <span className="text-slate-200 text-right">{booking.city}</span>
          </div>
        </div>

        {/* Footer info & Navigation */}
        <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-400 text-center sm:text-left">
            Payment is due on completion of service.
          </p>
          <Link
            href="/"
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-orange-500 hover:bg-orange-600 text-white font-semibold text-xs transition-colors text-center shadow-lg shadow-orange-500/20"
          >
            Back to Assistant
          </Link>
        </div>
      </div>
    </div>
  );
}
