import { Commit } from 'vuex';
import { defaultState } from '@/store/settings/state';
import { SettingsState } from '@/store/settings/types';
import { Writeable } from '@/types';

export function loadFrontendSettings(commit: Commit, value: string) {
  try {
    const defaultSettings: Writeable<SettingsState> = defaultState();
    const settings = JSON.parse(value);
    for (const [key, value] of Object.entries(defaultSettings)) {
      if (typeof settings[key] === typeof value) {
        // @ts-ignore
        defaultSettings[key] = settings[key];
      }
    }

    // eslint-disable-next-line no-empty
  } catch (e) {}
}
