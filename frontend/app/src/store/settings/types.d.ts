import { DEFI_SETUP_DONE } from '@/store/settings/consts';

export interface SettingsState {
  readonly [DEFI_SETUP_DONE]: boolean;
}

export type FrontendSettingsPayload = {
  +readonly [P in keyof SettingsState]+?: SettingsState[P];
};
