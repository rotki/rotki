/**
 * Wallet Bridge Protocol Constants
 */

// Custom Rotki RPC Methods
export const ROTKI_RPC_METHODS = {
  // Provider management methods
  GET_AVAILABLE_PROVIDERS: 'rotki_getAvailableProviders',
  GET_SELECTED_PROVIDER: 'rotki_getSelectedProvider',

  // Bridge health check - doesn't require RPC provider
  PING: 'rotki_ping',
  SELECT_PROVIDER: 'rotki_selectProvider',
} as const;

// Response values
export const ROTKI_RPC_RESPONSES = {
  PONG: 'pong',
} as const;

// Notification types
export const BRIDGE_NOTIFICATION_TYPES = {
  CLOSE_TAB: 'close_tab',
  RECONNECTED: 'reconnected',
  WALLET_EVENT: 'wallet_event',
} as const;

// WebSocket event types
export const WALLET_EVENT_TYPES = {
  ACCOUNTS_CHANGED: 'accountsChanged',
  CHAIN_CHANGED: 'chainChanged',
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
} as const;

// Error codes
export const BRIDGE_ERROR_CODES = {
  INTERNAL_ERROR: -32603,
  INVALID_PARAMS: -32602,
  NO_PROVIDER: -32001,
} as const;
