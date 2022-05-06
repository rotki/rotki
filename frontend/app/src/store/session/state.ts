import { TimeFramePeriod } from '@rotki/common/lib/settings/graphs';
import {
  defaultAccountingSettings,
  defaultGeneralSettings
} from '@/data/factories';
import { PrivacyMode, SessionState } from '@/store/session/types';
import { isAnimationsEnabled } from '@/store/utils';

export const defaultState: () => SessionState = () => ({
  newAccount: false,
  logged: false,
  loginComplete: false,
  username: '',
  generalSettings: defaultGeneralSettings(),
  accountingSettings: defaultAccountingSettings(),
  privacyMode: PrivacyMode.NORMAL,
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
  lastBalanceSave: 0,
  lastDataUpload: 0,
  timeframe: TimeFramePeriod.ALL,
  showUpdatePopup: false,
  animationsEnabled: isAnimationsEnabled?.() ?? false
});

export const state: SessionState = defaultState();
