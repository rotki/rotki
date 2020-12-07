import { TIMEFRAME_ALL } from '@/components/dashboard/const';
import { DASHBOARD_TIMEFRAME, DEFI_SETUP_DONE } from '@/store/settings/consts';
import { SettingsState } from '@/store/settings/types';

export const defaultState: () => SettingsState = () => ({
  [DEFI_SETUP_DONE]: false,
  [DASHBOARD_TIMEFRAME]: TIMEFRAME_ALL
});

export const state: SettingsState = defaultState();
