export const AddressStatus = {
  COMPLETE: 'complete',
  DECODING: 'decoding',
  PENDING: 'pending',
  QUERYING: 'querying',
} as const;

export type AddressStatus = (typeof AddressStatus)[keyof typeof AddressStatus];

export const AddressSubtype = {
  BITCOIN: 'bitcoin',
  EVM: 'evm',
  EVMLIKE: 'evmlike',
  SOLANA: 'solana',
} as const;

export type AddressSubtype = (typeof AddressSubtype)[keyof typeof AddressSubtype];

export const AddressStep = {
  INTERNAL: 'internal',
  TOKENS: 'tokens',
  TRANSACTIONS: 'transactions',
} as const;

export type AddressStep = (typeof AddressStep)[keyof typeof AddressStep];

export interface AddressProgress {
  address: string;
  status: AddressStatus;
  step?: AddressStep;
  period?: [number, number];
  originalPeriodEnd?: number;
  originalPeriodStart?: number;
  periodProgress?: number;
  subtype: AddressSubtype;
}

export interface ChainProgress {
  chain: string;
  addresses: AddressProgress[];
  total: number;
  completed: number;
  inProgress: number;
  pending: number;
  progress: number;
}

export const LocationStatus = {
  COMPLETE: 'complete',
  PENDING: 'pending',
  QUERYING: 'querying',
} as const;

export type LocationStatus = (typeof LocationStatus)[keyof typeof LocationStatus];

export interface LocationProgress {
  location: string;
  name: string;
  status: LocationStatus;
  eventType?: string;
}

export interface DecodingProgress {
  chain: string;
  total: number;
  processed: number;
  progress: number;
}

export interface ProtocolCacheProgress {
  chain: string;
  protocol: string;
  total: number;
  processed: number;
  progress: number;
}

export const SyncPhase = {
  COMPLETE: 'complete',
  IDLE: 'idle',
  SYNCING: 'syncing',
} as const;

export type SyncPhase = (typeof SyncPhase)[keyof typeof SyncPhase];

export interface SyncProgressState {
  phase: SyncPhase;
  overallProgress: number;

  chains: ChainProgress[];
  totalChains: number;
  completedChains: number;

  locations: LocationProgress[];
  totalLocations: number;
  completedLocations: number;

  decoding: DecodingProgress[];

  protocolCache: ProtocolCacheProgress[];

  totalAccounts: number;
  completedAccounts: number;

  isActive: boolean;
  canDismiss: boolean;
}
