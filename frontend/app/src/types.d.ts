import type { Interop } from '@shared/ipc';

interface WalletBridgeApi {
  // Connection management
  isEnabled: () => boolean;
  isConnected: () => boolean;
  enable: () => Promise<void>;
  disable: () => Promise<void>;

  // Bridge server management
  openWalletBridge: () => Promise<void>;
  walletBridgeConnect: () => Promise<boolean>;
  walletBridgeHttpListening: () => Promise<boolean>;
  walletBridgeWebSocketListening: () => Promise<boolean>;
  walletBridgeClientReady: () => Promise<boolean>;

  // RPC requests
  request: (request: RpcRequest) => Promise<any>;

  // Event management
  addEventListener: (eventName: string, callback: (data: any) => void) => void;
  removeEventListener: (eventName: string) => void;

  // EIP-6963 Provider Detection
  getAvailableProviders: () => Promise<EIP6963ProviderDetail[]>;
  selectProvider: (uuid: string) => Promise<boolean>;
  getSelectedProvider: () => Promise<EIP6963ProviderDetail | null>;
}

interface Request {
  readonly method: string;
  readonly params: readonly Record<string, unknown>[];
}

export interface RpcRequest {
  method: string;
  params?: unknown[];
}

interface Permission {
  readonly parentCapability: string;
}

declare global {
  interface Window {
    interop?: Interop;
    ethereum?: EIP1193Provider;
    walletBridge?: WalletBridgeApi;
  }

  interface WindowEventMap {
    'eip6963:announceProvider': CustomEvent;
  }
}

// Handle Metamask and other wallet extension import
export interface EIP6963ProviderInfo {
  rdns: string;
  uuid: string;
  name: string;
  icon: string;
}

export interface EIP6963ProviderDetail {
  info: EIP6963ProviderInfo;
  provider: EIP1193Provider;
}

export interface EIP6963AnnounceProviderEvent {
  detail: EIP6963ProviderDetail;
}

// EIP-1193 Provider Events
export interface EIP1193ProviderEvents {
  connect: [{ chainId: string }];
  disconnect: [{ code: number; message: string }];
  accountsChanged: [string[]];
  chainChanged: [string];
  message: [{ type: string; data: unknown }];
  error: [Error];
}

export type EIP1193EventName = keyof EIP1193ProviderEvents;

export interface EIP1193Provider {
  readonly isStatus?: boolean;
  readonly connected?: boolean;
  readonly isRotkiBridge?: boolean;
  readonly host?: string;
  readonly path?: string;
  sendAsync?: (
    request: RpcRequest,
    callback: (error: Error | null, response: unknown) => void
  ) => void;
  send?: (
    request: RpcRequest,
    callback: (error: Error | null, response: unknown) => void
  ) => void;
  request: <T = unknown>(request: RpcRequest) => Promise<T>;
  on?: <K extends EIP1193EventName>(
    event: K,
    callback: (...args: EIP1193ProviderEvents[K]) => void
  ) => void;
  removeListener?: <K extends EIP1193EventName>(
    event: K,
    callback: (...args: EIP1193ProviderEvents[K]) => void
  ) => void;
  off?: <K extends EIP1193EventName>(
    event: K,
    callback: (...args: EIP1193ProviderEvents[K]) => void
  ) => void;
  disconnect?: () => Promise<void>;
}

export interface WebVersion {
  readonly platform: string;
  readonly userAgent: string;
}
