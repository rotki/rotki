import type { WebSocket } from 'ws';

export interface WalletBridgeIpcCallbacks {
  sendIpcMessage: (channel: string, ...args: any[]) => void;
}

export interface PendingRequest {
  resolve: (value: any) => void;
  reject: (error: Error) => void;
  connectionId: number;
}

export interface ConnectionInfo {
  id: number;
  websocket: WebSocket;
  isActive: boolean;
}

// Constants
export const IDLE_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

export const REQUEST_TIMEOUT_MS = 60 * 1000; // 60 seconds

export const WEBSOCKET_PATH = '/wallet-bridge';

export const IPC_CONNECTION_STATUS_CHANNEL = 'WALLET_BRIDGE_CONNECTION_STATUS';

export const IPC_BRIDGE_EVENT_CHANNEL = 'WALLET_BRIDGE_EVENT';
