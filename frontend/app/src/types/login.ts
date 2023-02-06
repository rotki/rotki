import { z } from 'zod';
import { type Exchange } from '@/types/exchanges';
import { type UserSettingsModel } from '@/types/user';

export type SyncApproval = 'yes' | 'no' | 'unknown';

export interface LoginCredentials {
  readonly username: string;
  readonly password: string;
  readonly syncApproval?: SyncApproval;
}

export interface PremiumSetup {
  readonly apiKey: string;
  readonly apiSecret: string;
  readonly submitUsageAnalytics: boolean;
  readonly syncDatabase: boolean;
}

export const AccountSession = z.record(
  z.enum(['loggedin', 'loggedout'] as const)
);

export type AccountSession = z.infer<typeof AccountSession>;

export const SyncConflictPayload = z.object({
  localLastModified: z.number(),
  remoteLastModified: z.number()
});

export type SyncConflictPayload = z.infer<typeof SyncConflictPayload>;

export interface SyncConflict {
  readonly message: string;
  readonly payload: SyncConflictPayload | null;
}

export class SyncConflictError extends Error {
  readonly payload: SyncConflictPayload;

  constructor(message: string, payload: SyncConflictPayload) {
    super(message);
    this.payload = payload;
    this.name = 'SyncConflictError';
  }
}

export interface CreateAccountPayload {
  readonly credentials: LoginCredentials;
  premiumSetup?: PremiumSetup;
}

export interface UnlockPayload {
  settings: UserSettingsModel;
  exchanges: Exchange[];
  username: string;
  fetchData?: boolean;
}

export interface CurrentDbUpgradeProgress {
  percentage: number;
  totalPercentage: number;
  currentStep: number;
  totalSteps: number;
  currentVersion: number;
  fromVersion: number;
  toVersion: number;
  description?: string;
}
