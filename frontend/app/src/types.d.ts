import type { Interop } from '@shared/ipc';

interface Request {
  readonly method: string;
  readonly params: Record<string, any>[];
}

interface Permission {
  readonly parentCapability: string;
}

declare global {
  interface Window {
    interop?: Interop;
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

export interface EIP1193Provider {
  isStatus?: boolean;
  host?: string;
  path?: string;
  sendAsync?: (
    request: { method: string; params?: Array<unknown> },
    callback: (error: Error | null, response: unknown) => void
  ) => void;
  send?: (
    request: { method: string; params?: Array<unknown> },
    callback: (error: Error | null, response: unknown) => void
  ) => void;
  request: (request: Request) => Promise<Permission[] | string[]>;
}

export interface WebVersion {
  readonly platform: string;
  readonly userAgent: string;
}
