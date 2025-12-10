import type { Exchange } from '@/types/exchanges';
import type { UserSettingsModel } from '@/types/user';
import { z } from 'zod/v4';

export type SyncApproval = 'yes' | 'no' | 'unknown';

export interface BasicLoginCredentials {
  readonly username: string;
  readonly password: string;
}

export interface LoginCredentials extends BasicLoginCredentials {
  readonly syncApproval?: SyncApproval;
  readonly resumeFromBackup?: boolean;
}

export interface PremiumSetup {
  readonly apiKey: string;
  readonly apiSecret: string;
  readonly syncDatabase: boolean;
}

interface InitialSettings {
  readonly submitUsageAnalytics: boolean;
}

export const AccountSession = z.record(z.string(), z.enum(['loggedin', 'loggedout'] as const));

export type AccountSession = z.infer<typeof AccountSession>;

export const SyncConflictPayload = z.object({
  localLastModified: z.number(),
  remoteLastModified: z.number(),
});

export type SyncConflictPayload = z.infer<typeof SyncConflictPayload>;

export interface SyncConflict {
  readonly message: string;
  readonly payload: SyncConflictPayload | null;
}

export interface IncompleteUpgradeConflict {
  readonly message: string;
}

export class SyncConflictError extends Error {
  readonly payload: SyncConflictPayload;

  constructor(message: string, payload: SyncConflictPayload) {
    super(message);
    this.payload = payload;
    this.name = 'SyncConflictError';
  }
}

export class IncompleteUpgradeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'IncompleteUpgradeError';
  }
}

export interface CreateAccountPayload {
  readonly credentials: LoginCredentials;
  readonly initialSettings: InitialSettings;
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
