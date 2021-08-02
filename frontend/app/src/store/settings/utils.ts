import {
  TimeFramePeriod,
  TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';
import { Commit } from 'vuex';
import { axiosCamelCaseTransformer } from '@/services/axios-tranformers';
import { defaultState } from '@/store/settings/state';
import { SettingsState } from '@/store/settings/types';
import { Writeable } from '@/types';

export function loadFrontendSettings(commit: Commit, value: string) {
  try {
    let requiresUpdate = false;
    const loadedSettings: Writeable<SettingsState> = defaultState();
    const settings = axiosCamelCaseTransformer(JSON.parse(value));

    for (const [key, value] of Object.entries(loadedSettings)) {
      if (typeof settings[key] === typeof value) {
        // @ts-ignore
        loadedSettings[key] = settings[key];
        requiresUpdate = true;
      }
    }

    if (requiresUpdate) {
      commit('settings/restore', loadedSettings, { root: true });
    }

    // eslint-disable-next-line no-empty
  } catch (e) {}
}

export function isPeriodAllowed(period: TimeFrameSetting): boolean {
  return (
    period === TimeFramePeriod.WEEK || period === TimeFramePeriod.TWO_WEEKS
  );
}
