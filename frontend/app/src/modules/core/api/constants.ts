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

/** Default maximum number of retry attempts after the initial request fails */
export const DEFAULT_MAX_RETRIES = 2;

/** Default base delay in milliseconds between retries (20 seconds) */
export const DEFAULT_RETRY_DELAY = 20_000;
