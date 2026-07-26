import type { BaseFetchOptions } from './types';

/**
 * JSON with a fallback, since a dedupe key must be derivable from any body the caller passes,
 * including values JSON refuses (cycles, BigInt). Two unstringifiable bodies of the same type collide,
 * which only costs a missed dedupe, never a wrong one, because the method, url and query still differ.
 */
export function safeStringify(value: unknown): string {
  try {
    return JSON.stringify(value);
  }
  catch {
    return `[unstringifiable:${typeof value}]`;
  }
}

/** Identifies a request for deduplication: same method, url, query and body means same request. */
export function createDedupeKey(url: string, options: BaseFetchOptions): string {
  const method = options.method ?? 'GET';
  const body = options.body ? safeStringify(options.body) : '';
  const query = options.query ? safeStringify(options.query) : '';
  return `${method}:${url}:${query}:${body}`;
}

/** Unique per queued request, only ever compared for equality within one session. */
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
}
