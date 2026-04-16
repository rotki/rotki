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

export type RequestPriorityLevel = (typeof RequestPriority)[keyof typeof RequestPriority];
