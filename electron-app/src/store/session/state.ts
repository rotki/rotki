import { defaultAccountingSettings, defaultSettings } from '@/data/factories';
import { AccountingSettings, GeneralSettings, Tags } from '@/typing/types';

export interface SessionState {
  newAccount: boolean;
  logged: boolean;
  username: string;
  settings: GeneralSettings;
  accountingSettings: AccountingSettings;
  premium: boolean;
  premiumSync: boolean;
  nodeConnection: boolean;
  syncConflict: string;
  tags: Tags;
}

export const defaultState: () => SessionState = () => ({
  newAccount: false,
  logged: false,
  username: '',
  settings: defaultSettings(),
  accountingSettings: defaultAccountingSettings(),
  premium: false,
  premiumSync: false,
  nodeConnection: false,
  syncConflict: '',
  tags: {}
});

export const state: SessionState = defaultState();
