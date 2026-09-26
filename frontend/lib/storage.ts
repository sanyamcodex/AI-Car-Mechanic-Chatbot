import { STORAGE_ACTIVE, STORAGE_CONV_IDS } from './constants';

export function getConversationIds(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_CONV_IDS);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.slice(0, 20) : [];
  } catch {
    return [];
  }
}

export function addConversationId(id: string): void {
  if (typeof window === 'undefined') return;
  try {
    const ids = getConversationIds().filter((x) => x !== id);
    ids.unshift(id);
    localStorage.setItem(STORAGE_CONV_IDS, JSON.stringify(ids.slice(0, 20)));
  } catch {
    // ignore
  }
}

export function removeConversationId(id: string): void {
  if (typeof window === 'undefined') return;
  try {
    const ids = getConversationIds().filter((x) => x !== id);
    localStorage.setItem(STORAGE_CONV_IDS, JSON.stringify(ids));
  } catch {
    // ignore
  }
}

export function getActiveConversationId(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return localStorage.getItem(STORAGE_ACTIVE);
  } catch {
    return null;
  }
}

export function setActiveConversationId(id: string | null): void {
  if (typeof window === 'undefined') return;
  try {
    if (id) {
      localStorage.setItem(STORAGE_ACTIVE, id);
    } else {
      localStorage.removeItem(STORAGE_ACTIVE);
    }
  } catch {
    // ignore
  }
}
