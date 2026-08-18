/** Default request timeout in milliseconds (30 seconds) */
export const DEFAULT_TIMEOUT = 30_000;

/** Extended timeout for long-running task operations in milliseconds (90 seconds) */
export const TASKS_TIMEOUT = 90_000;

/**
 * File downloads (reports, snapshots, skipped-event exports) in milliseconds (10 minutes).
 * These stream a whole file the backend assembles on demand, so the 30s default is far too short.
 * It only mattered once timeouts started being honoured at all - see {@link combineAbortSignals}.
 */
export const DOWNLOAD_TIMEOUT = 600_000;

/**
 * Response fields whose value is a map keyed by chain id rather than a record of fields.
 *
 * Passed as `skipCamelCaseKeys` so the response transformer leaves their contents as the backend
 * sent them. It cannot tell a field name from a chain id, so otherwise it rewrites the ids:
 * `polygon_pos` arrives as `polygonPos` while single-word ids like `base` are untouched, and every
 * lookup by chain id then matches some entries and misses the rest.
 *
 * Named in their wire spelling, and shared, because these settings reach the app on more than one
 * endpoint: a request that reads them without this gets its own mangled copy.
 */
export const CHAIN_KEYED_SETTINGS: string[] = ['disabled_chain_queries', 'evm_indexers_order'];

/** Default maximum number of retry attempts after the initial request fails */
export const DEFAULT_MAX_RETRIES = 2;

/** Default base delay in milliseconds between retries (20 seconds) */
export const DEFAULT_RETRY_DELAY = 20_000;

/**
 * The upstream a request addresses. Everything reaches the same origin; the
 * target picks the path prefix under it (`/api/1/` for core, `/colibri` for
 * colibri, which the starling proxy strips) and, with it, the queue the request
 * is scheduled on.
 */
export const RequestTarget = {
  COLIBRI: 'colibri',
  CORE: 'core',
} as const;

export type RequestTarget = (typeof RequestTarget)[keyof typeof RequestTarget];
