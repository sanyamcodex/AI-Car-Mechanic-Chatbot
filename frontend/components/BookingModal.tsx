'use client';

import React, { useState, useId } from 'react';
import { DiagnosisInfo, BookingInfo } from '../lib/types';
import { createBooking, ApiError } from '../lib/api';

interface BookingModalProps {
  isOpen: boolean;
  onClose: () => void;
  diagnosis?: DiagnosisInfo | null;
  conversationId?: string | null;
  onSuccess: (booking: BookingInfo) => void;
}

const SUPPORTED_CITIES = ['Meerut', 'Delhi', 'Noida', 'Gurugram', 'Ghaziabad'];

export const BookingModal: React.FC<BookingModalProps> = ({
  isOpen,
  onClose,
  diagnosis,
  conversationId,
  onSuccess,
}) => {
  const [customerName, setCustomerName] = useState('');
  const [phone, setPhone] = useState('');
  const [city, setCity] = useState(SUPPORTED_CITIES[0]);
  const [scheduledAt, setScheduledAt] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [alternatives, setAlternatives] = useState<string[]>([]);
  const [idempotencyKey] = useState(() => 'bk-' + Math.random().toString(36).substring(2, 12));

  if (!isOpen) return null;

  const validate = (): string | null => {
    if (customerName.trim().length < 2 || customerName.trim().length > 60) {
      return 'Customer name must be between 2 and 60 characters.';
    }
    const cleanPhone = phone.replace(/\D/g, '');
    if (!/^[6-9]\d{9}$/.test(cleanPhone)) {
      return 'Please enter a valid 10-digit Indian phone number starting with 6-9.';
    }
    if (!city) {
      return 'Please select a service city.';
    }
    if (!scheduledAt) {
      return 'Please choose a preferred appointment slot.';
    }

    const date = new Date(scheduledAt);
    if (isNaN(date.getTime())) {
      return 'Invalid date selected.';
    }
    if (date.getMinutes() !== 0 || date.getSeconds() !== 0) {
      return 'Appointments must be booked on the hour (e.g. 10:00, 14:00).';
    }
    const hour = date.getHours();
    if (hour < 9 || hour > 18) {
      return 'Appointments must be scheduled within business hours (9 AM – 6 PM).';
    }
    const minAdvance = new Date(Date.now() + 2 * 60 * 60 * 1000);
    if (date < minAdvance) {
      return 'Appointments must be booked at least 2 hours in advance.';
    }

    return null;
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setErrorMessage(null);
    setAlternatives([]);

    const validationErr = validate();
    if (validationErr) {
      setErrorMessage(validationErr);
      return;
    }

    setLoading(true);
    try {
      const cleanPhone = phone.replace(/\D/g, '');
      const booking = await createBooking(
        {
          customer_name: customerName.trim(),
          phone: cleanPhone,
          city,
          scheduled_at: new Date(scheduledAt).toISOString(),
          service_key: diagnosis?.service?.key || null,
          conversation_id: conversationId || null,
          idempotency_key: idempotencyKey,
        },
        idempotencyKey
      );

      onSuccess(booking);
      onClose();
    } catch (err: any) {
      console.error('Booking submission error:', err);
      if (err instanceof ApiError && err.status === 409) {
        setErrorMessage('The chosen slot is currently booked. Please choose an alternative:');
        if (err.details?.alternatives && Array.isArray(err.details.alternatives)) {
          setAlternatives(err.details.alternatives);
        }
      } else {
        setErrorMessage(err.message || 'Failed to complete booking. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAlternative = (slotIso: string) => {
    // Format to datetime-local input value (YYYY-MM-DDTHH:00)
    const d = new Date(slotIso);
    const pad = (n: number) => n.toString().padStart(2, '0');
    const localStr = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:00`;
    setScheduledAt(localStr);
    setErrorMessage(null);
    setAlternatives([]);
  };

  const formatSlotLabel = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl relative">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
          disabled={loading}
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Modal Header */}
        <div className="mb-5">
          <span className="text-[11px] font-bold text-orange-400 uppercase tracking-wider">
            Confirm Appointment
          </span>
          <h2 className="text-xl font-bold text-white mt-1">Book Certified Mechanic</h2>
          {diagnosis?.service && (
            <p className="text-xs text-slate-300 mt-1">
              Service: <span className="font-semibold text-white">{diagnosis.service.name}</span> (~₹
              {diagnosis.service.price_min.toLocaleString()}–{diagnosis.service.price_max.toLocaleString()})
            </p>
          )}
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="bg-red-950/80 border border-red-800 rounded-xl p-3 mb-4 text-xs text-red-200">
            <p className="font-semibold">{errorMessage}</p>

            {/* Conflict Alternatives */}
            {alternatives.length > 0 && (
              <div className="mt-2.5 flex flex-wrap gap-2">
                {alternatives.map((alt, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSelectAlternative(alt)}
                    className="px-2.5 py-1 rounded-lg bg-orange-600 hover:bg-orange-500 text-white font-medium text-xs transition-colors shadow"
                  >
                    {formatSlotLabel(alt)}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Form Fields */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
            <input
              type="text"
              required
              placeholder="e.g. Rajesh Sharma"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              disabled={loading}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-orange-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              10-Digit Mobile Number
            </label>
            <input
              type="tel"
              required
              placeholder="e.g. 9812345670"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              disabled={loading}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">City</label>
            <select
              value={city}
              onChange={(e) => setCity(e.target.value)}
              disabled={loading}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-orange-500 cursor-pointer"
            >
              {SUPPORTED_CITIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Date &amp; Time (Hourly 9 AM – 6 PM)
            </label>
            <input
              type="datetime-local"
              required
              step="3600"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              disabled={loading}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-orange-500"
            />
          </div>

          {/* Buttons */}
          <div className="pt-2 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2.5 rounded-xl bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white font-bold text-xs shadow-lg shadow-orange-500/20 transition-all flex items-center gap-2 cursor-pointer"
            >
              {loading ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Assigning Specialist...</span>
                </>
              ) : (
                <span>Confirm &amp; Book</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
