import { TimeFramePeriod } from '@/components/dashboard/types';
import { DASHBOARD_TIMEFRAME, DEFI_SETUP_DONE } from '@/store/settings/consts';

export interface SettingsState {
  readonly [DEFI_SETUP_DONE]: boolean;
  readonly [DASHBOARD_TIMEFRAME]: TimeFramePeriod;
}

export type FrontendSettingsPayload = {
  +readonly [P in keyof SettingsState]+?: SettingsState[P];
};
