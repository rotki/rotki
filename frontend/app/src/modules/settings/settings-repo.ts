import type { Ref } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type { SessionSettings } from '@/modules/session/types';
import type { AccountingSettings, GeneralSettings } from '@/modules/settings/types/user-settings';
import { TimeFramePeriod } from '@rotki/common';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { defaultAccountingSettings, defaultGeneralSettings } from '@/modules/settings/factories';
import { getRegistryEntry, registryEntries } from '@/modules/settings/settings-registry';
import { type FrontendSettings, getDefaultFrontendSettings } from '@/modules/settings/types/frontend-settings';

/** Resolves each registry entry that declares a `mirror` factory to its external shared ref, once. */
function resolveMirrors(): Map<string, Ref<unknown>> {
  const mirrors = new Map<string, Ref<unknown>>();
  for (const [key, entry] of registryEntries()) {
    if (entry.mirror)
      mirrors.set(key, entry.mirror());
  }
  return mirrors;
}

const useSharedLocalStorage = createSharedComposable(useLocalStorage);
const isAnimationEnabledSetting = useSharedLocalStorage('rotki.animations_enabled', true);

function defaultSessionSettings(): SessionSettings {
  return {
    animationsEnabled: get<boolean>(isAnimationEnabledSetting),
    timeframe: TimeFramePeriod.ALL,
  };
}

/**
 * Single source of truth for the four settings channels. Holds each channel's already-parsed
 * settings object (the same objects the four per-channel stores used to hold) and the imperative
 * update methods that mutate them. Feature code never reads these refs directly: it goes through
 * `useSetting` (reads) and `settingsWriter` / `useSettingModel` (writes), both of which route via
 * the settings registry. Only the read primitive, the write pipeline (`useSettingsOperations`,
 * `useSettingsWriter`) and login bootstrap (`useSessionSettings`) touch the repo.
 */
export const useSettingsRepo = defineStore('settings', () => {
  const { defaultCurrency } = useCurrencies();

  const general = ref<GeneralSettings>(defaultGeneralSettings(get(defaultCurrency)));
  const accounting = ref<AccountingSettings>(defaultAccountingSettings());
  const frontend = ref<FrontendSettings>(markRaw(getDefaultFrontendSettings()));
  const session = ref<SessionSettings>(defaultSessionSettings());

  const mirrors = resolveMirrors();

  const updateGeneral = (settings: GeneralSettings): void => {
    set(general, { ...get(general), ...settings });
  };

  const updateAccounting = (settings: AccountingSettings): void => {
    set(accounting, { ...get(accounting), ...settings });
  };

  // Runs the registry-declared effects and mirror syncs for the frontend keys that just changed.
  // Effects (e.g. reconfiguring BigNumber's format) get the whole merged object; mirrors (e.g. the
  // standalone `itemsPerPage` global ref) are pushed the new value, guarded to avoid a write echo.
  const applyFrontendSideEffects = (changedKeys: string[], merged: FrontendSettings): void => {
    for (const key of changedKeys) {
      const entry = getRegistryEntry(key);
      if (!entry)
        continue;
      entry.effects?.forEach(effect => effect(merged));
      const mirror = mirrors.get(key);
      const value: unknown = Reflect.get(merged, key);
      if (mirror && get(mirror) !== value)
        set(mirror, value);
    }
  };

  const updateFrontend = (settings: Partial<FrontendSettings>): void => {
    const merged = { ...get(frontend), ...settings };
    set(frontend, merged);
    applyFrontendSideEffects(Object.keys(settings), merged);
  };

  const updateSession = (settings: Partial<SessionSettings>): ActionStatus => {
    set(session, { ...get(session), ...settings });
    return { success: true };
  };

  const setAnimationsEnabled = (enabled: boolean): void => {
    set(isAnimationEnabledSetting, enabled);
    updateSession({ animationsEnabled: enabled });
  };

  return {
    accounting,
    frontend,
    general,
    session,
    setAnimationsEnabled,
    updateAccounting,
    updateFrontend,
    updateGeneral,
    updateSession,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSettingsRepo, import.meta.hot));
