import type { Ref } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type { SessionSettings } from '@/modules/session/types';
import type { AccountingSettings, GeneralSettings } from '@/modules/settings/types/user-settings';
import { TimeFramePeriod } from '@rotki/common';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useAnimationsEnabled } from '@/modules/session/use-animations-enabled';
import { defaultAccountingSettings, defaultGeneralSettings } from '@/modules/settings/factories';
import { Channel, type RegistryEntry, type SettingChannel } from '@/modules/settings/settings-channels';
import { registryEntries } from '@/modules/settings/settings-registry';
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

/**
 * Reverse index from a channel's wire field name to its `[logicalKey, entry]`. The repo's update
 * methods receive wire-keyed payloads, but effects and mirrors are declared on (and mirrors keyed by)
 * the logical registry key. This lets the effect runner resolve the right entry even when a key's
 * `wireKey` differs from its logical key, instead of assuming the two are identical.
 */
function buildWireIndex(): Map<string, readonly [string, RegistryEntry]> {
  const index = new Map<string, readonly [string, RegistryEntry]>();
  for (const [logicalKey, entry] of registryEntries()) {
    // Projected keys are read-only derivations with no wire field, so they never appear in a payload.
    if (entry.project)
      continue;
    index.set(`${entry.channel}:${entry.wireKey ?? logicalKey}`, [logicalKey, entry]);
  }
  return index;
}

function defaultSessionSettings(): SessionSettings {
  return {
    animationsEnabled: get<boolean>(useAnimationsEnabled()),
    timeframe: TimeFramePeriod.ALL,
  };
}

/**
 * Holds the four settings channels and the methods that mutate them.
 *
 * @remarks
 * Feature code must not read these refs or call these methods directly. Reads go through
 * `useSetting`, writes through `settingsWriter` / `useSettingModel`, both routing via the settings
 * registry. Only the read primitive, the write pipeline and login bootstrap touch the repo.
 */
export const useSettingsRepo = defineStore('settings', () => {
  const { defaultCurrency } = useCurrencies();

  const general = ref<GeneralSettings>(defaultGeneralSettings(get(defaultCurrency)));
  const accounting = ref<AccountingSettings>(defaultAccountingSettings());
  const frontend = ref<FrontendSettings>(markRaw(getDefaultFrontendSettings()));
  const session = ref<SessionSettings>(defaultSessionSettings());

  const mirrors = resolveMirrors();
  const wireIndex = buildWireIndex();

  // Runs the registry-declared effects and mirror syncs for the keys of a channel that just changed.
  // `changedWireKeys` are the wire field names of the merged object; each is resolved to its logical
  // registry entry via `wireIndex`. Effects (e.g. reconfiguring BigNumber's format) get the whole
  // merged object; mirrors (e.g. the `itemsPerPage` global ref, or animations' localStorage) are
  // pushed the new value, guarded to avoid a write echo.
  const applySideEffects = (channel: SettingChannel, changedWireKeys: string[], merged: object): void => {
    for (const wireKey of changedWireKeys) {
      const found = wireIndex.get(`${channel}:${wireKey}`);
      if (!found)
        continue;
      const [logicalKey, entry] = found;
      entry.effects?.forEach(effect => effect(merged));
      const mirror = mirrors.get(logicalKey);
      if (!mirror)
        continue;
      const value: unknown = Reflect.get(merged, wireKey);
      if (get(mirror) !== value)
        set(mirror, value);
    }
  };

  const updateGeneral = (settings: GeneralSettings): void => {
    set(general, { ...get(general), ...settings });
  };

  const updateAccounting = (settings: AccountingSettings): void => {
    set(accounting, { ...get(accounting), ...settings });
  };

  const updateFrontend = (settings: Partial<FrontendSettings>): void => {
    const merged = { ...get(frontend), ...settings };
    set(frontend, merged);
    applySideEffects(Channel.frontend, Object.keys(settings), merged);
  };

  const updateSession = (settings: Partial<SessionSettings>): ActionStatus => {
    const merged = { ...get(session), ...settings };
    set(session, merged);
    applySideEffects(Channel.session, Object.keys(settings), merged);
    return { success: true };
  };

  return {
    accounting,
    frontend,
    general,
    session,
    updateAccounting,
    updateFrontend,
    updateGeneral,
    updateSession,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSettingsRepo, import.meta.hot));
