import {
  defaultAccountingSettings,
  defaultGeneralSettings
} from '@/data/factories';
import { AccountingSettings, GeneralSettings, Tags } from '@/typing/types';

export interface SessionState {
  newAccount: boolean;
  logged: boolean;
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
}

export const defaultState: () => SessionState = () => ({
  newAccount: false,
  logged: false,
  username: '',
  generalSettings: defaultGeneralSettings(),
  accountingSettings: defaultAccountingSettings(),
  privacyMode: false,
  scrambleData: false,
  premium: false,
  premiumSync: false,
  nodeConnection: false,
  syncConflict: '',
  tags: {}
});

export const state: SessionState = defaultState();
