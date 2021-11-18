import { SyncConflictPayload } from '@/store/session/types';

export interface Credentials {
  readonly username: string;
  readonly password: string;
  readonly syncApproval?: SyncApproval;
  readonly apiKey?: string;
  readonly apiSecret?: string;
  readonly submitUsageAnalytics?: boolean;
}

export interface AccountSession {
  [account: string]: 'loggedin' | 'loggedout';
}

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
