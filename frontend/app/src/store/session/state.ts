import {
  defaultAccountingSettings,
  defaultGeneralSettings
} from '@/data/factories';
import { SessionState } from '@/store/session/types';
import { TIMEFRAME_ALL } from '@/store/settings/consts';

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
  syncConflict: {
    message: '',
    payload: null
  },
  tags: {},
  watchers: [],
  queriedAddresses: {},
  ignoredAssets: [],
  lastBalanceSave: 0,
  lastDataUpload: 0,
  timeframe: TIMEFRAME_ALL,
  prices: {}
});

export const state: SessionState = defaultState();
