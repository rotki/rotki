import {
  defaultAccountingSettings,
  defaultGeneralSettings
} from '@/data/factories';
import { SessionState } from '@/store/session/types';

export const defaultState: () => SessionState = () => ({
  newAccount: false,
  logged: false,
  loginComplete: false,
  username: '',
  generalSettings: defaultGeneralSettings(),
  accountingSettings: defaultAccountingSettings(),
  privacyMode: false,
  scrambleData: false,
  premium: false,
  premiumSync: false,
  nodeConnection: false,
  syncConflict: '',
  tags: {},
  watchers: [],
  queriedAddresses: {},
  ignoredAssets: []
});

export const state: SessionState = defaultState();
