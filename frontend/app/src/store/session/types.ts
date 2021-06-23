import {
  QueriedAddresses,
  Watcher,
  WatcherTypes
} from '@/services/session/types';
import { TimeFramePeriod } from '@/store/settings/types';
import { AccountingSettings, GeneralSettings, Tags } from '@/typing/types';

export interface SessionState {
  newAccount: boolean;
  logged: boolean;
  loginComplete: boolean;
  username: string;
  generalSettings: GeneralSettings;
  accountingSettings: AccountingSettings;
  premium: boolean;
  premiumSync: boolean;
  privacyMode: boolean;
  scrambleData: boolean;
  nodeConnection: boolean;
  syncConflict: SyncConflict;
  tags: Tags;
  watchers: Watcher<WatcherTypes>[];
  queriedAddresses: QueriedAddresses;
  ignoredAssets: string[];
  lastBalanceSave: number;
  lastDataUpload: number;
  timeframe: TimeFramePeriod;
}

export interface SyncConflictPayload {
  readonly localSize: string;
  readonly remoteSize: string;
  readonly localLastModified: number;
  readonly remoteLastModified: number;
}

export interface SyncConflict {
  readonly message: string;
  readonly payload: SyncConflictPayload | null;
}

export interface PremiumCredentialsPayload {
  readonly username: string;
  readonly apiKey: string;
  readonly apiSecret: string;
}

export interface ChangePasswordPayload {
  readonly currentPassword: string;
  readonly newPassword: string;
}
