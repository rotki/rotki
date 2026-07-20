export interface WalletBridgeIpcCallbacks {
  sendIpcMessage: (channel: string, ...args: any[]) => void;
}

export interface PendingRequest {
  resolve: (value: any) => void;
  reject: (error: Error) => void;
  connectionId: number;
}

// Constants
export const IDLE_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

export const REQUEST_TIMEOUT_MS = 60 * 1000; // 60 seconds

// How long quit waits for the wallet bridge server to release its handle
export const SERVER_CLOSE_TIMEOUT_MS = 2000; // 2 seconds

export const WEBSOCKET_PATH = '/wallet-bridge';

export const IPC_CONNECTION_STATUS_CHANNEL = 'WALLET_BRIDGE_CONNECTION_STATUS';

export const IPC_BRIDGE_EVENT_CHANNEL = 'WALLET_BRIDGE_EVENT';
