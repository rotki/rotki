import { Commit } from 'vuex';

export function loadFrontendSettings(commit: Commit, value: string) {
  try {
    const settings = JSON.parse(value);
    if (settings.defiSetupDone) {
      commit('defiSetup', settings.defiSetupDone);
    }
    // eslint-disable-next-line no-empty
  } catch (e) {}
}
