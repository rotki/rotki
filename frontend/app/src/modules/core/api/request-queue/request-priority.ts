/**
 * Predefined priority levels for request queue.
 * Higher values = processed first.
 */
export const RequestPriority = {
  /** Login, logout, session validation - always first */
  AUTH: 10,
  /** User-initiated actions requiring immediate feedback */
  CRITICAL: 8,
  /** Real-time data updates, WebSocket fallbacks */
  HIGH: 6,
  /** Standard API calls (default for most requests) */
  NORMAL: 4,
  /** Prefetching, non-urgent data loading */
  LOW: 2,
  /** Analytics, telemetry, non-essential background work */
  BACKGROUND: 0,
} as const;

/**
 * PUT, PATCH and DELETE are unambiguously a user changing something, and the user is waiting on the
 * result, so they outrank reads. POST is deliberately not in the set: this API uses it for filtered
 * reads (`/history/events`, `/names`, `/notes`) at least as often as for creation, so it says
 * nothing about intent on its own. A POST that really is a user action can pass `priority`.
 */
const MUTATION_METHODS: ReadonlySet<string> = new Set(['PUT', 'PATCH', 'DELETE']);

/**
 * Derived from the method rather than tagged at every call site: a rule nobody has to remember is
 * the only one that holds across ~300 of them.
 */
export function defaultPriorityFor(method?: string): number {
  return method && MUTATION_METHODS.has(method.toUpperCase())
    ? RequestPriority.CRITICAL
    : RequestPriority.NORMAL;
}

/** Advisory work, subject to the queue's background slot cap. */
export function isBackgroundPriority(priority: number): boolean {
  return priority <= RequestPriority.LOW;
}
