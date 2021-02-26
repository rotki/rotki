import { Commit } from 'vuex';
import { axiosCamelCaseTransformer } from '@/services/axios-tranformers';
import {
  REFRESH_1H,
  REFRESH_2H,
  REFRESH_30MIN,
  TIMEFRAME_TWO_WEEKS,
  TIMEFRAME_WEEK
} from '@/store/settings/consts';
import { defaultState } from '@/store/settings/state';
import {
  RefreshPeriod,
  SettingsState,
  TimeFrameSetting
} from '@/store/settings/types';
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
  return [TIMEFRAME_WEEK, TIMEFRAME_TWO_WEEKS].includes(period);
}

export const getPeriodInMs: (period: RefreshPeriod) => number = period => {
  let ms = 60 * 1000;
  if (period === REFRESH_30MIN) {
    ms *= 30;
  } else if (period === REFRESH_1H) {
    ms *= 120;
  } else if (period === REFRESH_2H) {
    ms *= 240;
  } else {
    ms = -1;
  }
  return ms;
};
