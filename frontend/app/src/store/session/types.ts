import {
  QueriedAddresses,
  Watcher,
  WatcherTypes
} from '@/services/session/types';
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
  syncConflict: string;
  tags: Tags;
  watchers: Watcher<WatcherTypes>[];
  defiSetupDone: boolean;
  queriedAddresses: QueriedAddresses;
}
