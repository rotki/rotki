/**
 * Shared configuration constants for wallet bridge operations
 * Used across both Electron renderer and browser contexts
 */

/**
 * Bridge proxy configuration (Electron renderer context)
 */
export const PROXY_CONFIG = {
  BRIDGE_PAGE_DELAY: 250,
  CONNECTION_TIMEOUT: 30000,
  HEALTH_CHECK_INTERVAL: 5000,
  RETRY_INTERVAL: 500,
  SERVER_TIMEOUT: 30000,
} as const;

/**
 * WebSocket client configuration (Browser context)
 */
export const CLIENT_CONFIG = {
  DEFAULT_BASE_PORT: 40011, // port + 1 from the default bridge port
  MAX_RETRIES: 5,
  RETRY_DELAY: 500,
} as const;
