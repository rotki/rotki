import { z } from 'zod';
import { logger } from '@/modules/core/common/logging/logging';

const INSTANCE_KEY = 'rotki.sigil.instance_id';
const CLIENT_KEY = 'rotki.sigil.client_ids';

const ClientIdCache = z.record(z.string(), z.string());

let instanceId: string | undefined;
let currentClientId: string | undefined;

/**
 * Stamped on every entry, not just the identify: upstream stores it per row, and a session covers
 * every account used on that machine that day, so a session-only link cannot tell them apart.
 */
export function getCurrentClientId(): string | undefined {
  return currentClientId;
}

export function setCurrentClientId(id: string): void {
  currentClientId = id;
}

export function clearCurrentClientId(): void {
  currentClientId = undefined;
}

/**
 * `crypto.randomUUID` needs a secure context, which a Docker instance reached over plain http on a
 * LAN IP is not, so it is only the first choice of three. `getRandomValues` has no such
 * restriction; the last resort keeps a weaker value working rather than throwing.
 */
function randomId(): string {
  if (typeof crypto !== 'undefined') {
    if (typeof crypto.randomUUID === 'function')
      return crypto.randomUUID();

    if (typeof crypto.getRandomValues === 'function') {
      const bytes = crypto.getRandomValues(new Uint8Array(16));
      // the v4 version and variant bits
      bytes[6] = (bytes[6] & 0x0F) | 0x40;
      bytes[8] = (bytes[8] & 0x3F) | 0x80;
      const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
      return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
    }
  }

  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
}

export function createClientId(): string {
  return randomId();
}

/**
 * Storage can throw (private mode, a quota), in which case the value lives only in memory for this
 * session, which is enough to keep one session's events consistent.
 */
export function getInstanceId(): string {
  if (instanceId)
    return instanceId;

  try {
    const stored = localStorage.getItem(INSTANCE_KEY);
    if (stored) {
      instanceId = stored;
      return stored;
    }

    const minted = randomId();
    localStorage.setItem(INSTANCE_KEY, minted);
    instanceId = minted;
    return minted;
  }
  catch {
    logger.debug('[sigil] storage unavailable, using an in-memory value');
    instanceId ??= randomId();
    return instanceId;
  }
}

function readCache(): Record<string, string> {
  try {
    const raw = localStorage.getItem(CLIENT_KEY);
    if (!raw)
      return {};

    const parsed = ClientIdCache.safeParse(JSON.parse(raw));
    return parsed.success ? parsed.data : {};
  }
  catch {
    return {};
  }
}

/**
 * A fallback, never the source of truth: only read when the settings hold nothing. Keyed by
 * username so two accounts on one machine do not read each other's.
 */
export function readCachedClientId(username: string): string | undefined {
  if (!username)
    return undefined;

  return readCache()[username];
}

export function cacheClientId(username: string, id: string): void {
  if (!username)
    return;

  try {
    localStorage.setItem(CLIENT_KEY, JSON.stringify({ ...readCache(), [username]: id }));
  }
  catch {
    logger.debug('[sigil] storage unavailable, not caching');
  }
}

export function resetSigilIdentity(): void {
  instanceId = undefined;
  try {
    localStorage.removeItem(INSTANCE_KEY);
    localStorage.removeItem(CLIENT_KEY);
  }
  catch {
    logger.debug('[sigil] storage unavailable, nothing to clear');
  }
}
