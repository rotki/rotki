import { FrontendSettings } from '@/types/frontend-settings';

export type SettingsState = FrontendSettings;
export const defaultState: () => SettingsState = () =>
  FrontendSettings.parse({});

export const state: SettingsState = defaultState();
