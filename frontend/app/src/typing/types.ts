import { BigNumber } from '@rotki/common';
import { AssetBalances } from '@/store/balances/types';
import { SyncConflictPayload } from '@/store/session/types';

export interface Credentials {
  readonly username: string;
  readonly password: string;
  readonly syncApproval?: SyncApproval;
  readonly apiKey?: string;
  readonly apiSecret?: string;
  readonly submitUsageAnalytics?: boolean;
}

export type ExchangeRates = { [key: string]: BigNumber };

export interface ExchangeInfo {
  readonly location: string;
  readonly balances: AssetBalances;
  readonly total: BigNumber;
}

export type ExchangeData = { [exchange: string]: AssetBalances };

export interface ProfitLossPeriod {
  readonly start: number;
  readonly end: number;
}

export interface AccountSession {
  [account: string]: 'loggedin' | 'loggedout';
}

export interface TaskResult<T> {
  outcome: T | null;
  status: 'completed' | 'not-found' | 'pending';
}

export const L2_LOOPRING = 'LRC';
export const L2_PROTOCOLS = [L2_LOOPRING] as const;
export type SupportedL2Protocol = typeof L2_PROTOCOLS[number];

export class SyncConflictError extends Error {
  readonly payload: SyncConflictPayload;

  constructor(message: string, payload: SyncConflictPayload) {
    super(message);
    this.payload = payload;
  }
}

export type SyncApproval = 'yes' | 'no' | 'unknown';

export interface UnlockPayload {
  readonly username: string;
  readonly password: string;
  readonly create?: boolean;
  readonly syncApproval?: SyncApproval;
  readonly apiKey?: string;
  readonly apiSecret?: string;
  readonly submitUsageAnalytics?: boolean;
  readonly restore?: boolean;
}

export type ExternalServiceName = 'etherscan' | 'cryptocompare' | 'loopring';

export interface ExternalServiceKey {
  readonly name: ExternalServiceName;
  readonly api_key: string;
}

export interface Tag {
  readonly name: string;
  readonly description: string;
  readonly background_color: string;
  readonly foreground_color: string;
}

export interface Tags {
  [tag: string]: Tag;
}
