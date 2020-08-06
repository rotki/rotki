import { DEFI_SETUP_DONE } from '@/store/settings/consts';
import { SettingsState } from '@/store/settings/types';

export const defaultState: () => SettingsState = () => ({
  [DEFI_SETUP_DONE]: false
});

export const state: SettingsState = defaultState();
