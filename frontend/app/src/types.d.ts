import { type Interop } from '@/electron-main/ipc';

interface Request {
  readonly method: string;
  readonly params: Record<string, any>[];
}

interface Caveat {
  readonly name: string;
  readonly value: string[];
}

interface Permission {
  readonly parentCapability: string;
  readonly caveats: Caveat[];
}

interface Provider {
  readonly isMetaMask?: boolean;
  readonly request: (request: Request) => Promise<Permission[]>;
}

declare global {
  interface Window {
    interop?: Interop;
    ethereum?: Provider;
  }
}

export type Writeable<T> = { -readonly [P in keyof T]: T[P] };

export type Properties<TObj, TResult> = {
  [K in keyof TObj]: TObj[K] extends TResult ? K : never;
}[keyof TObj];

export type Nullable<T> = T | null;

export interface WebVersion {
  readonly platform: string;
  readonly userAgent: string;
}
