import type { FrontendSettings, FrontendSettingsPayload } from '@/modules/settings/types/frontend-settings';
import type { GeneralSettings, SettingsUpdate } from '@/modules/settings/types/user-settings';
import { isEqual } from 'es-toolkit';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { compareVersions } from './compare-versions';
import {
  createSettingsSuggestions,
  getSuggestionKey,
  type PendingSuggestion,
  type SettingsSuggestion,
  type VersionSuggestions,
} from './settings-suggestions';
import { useSuggestionsStore } from './use-suggestions-store';

function getCurrentValue(
  suggestion: SettingsSuggestion,
  frontendSettings: FrontendSettings,
  generalSettings: GeneralSettings,
): unknown {
  if (suggestion.settingType === 'frontend')
    return frontendSettings[suggestion.key];
  return generalSettings[suggestion.key];
}

/**
 * Pure function that collects pending suggestions for a given settings state and app version.
 * Exported separately for testability without store mocking.
 */
export function collectPendingSuggestions(
  frontendSettings: FrontendSettings,
  generalSettings: GeneralSettings,
  appVersion: string,
  registry: VersionSuggestions[],
): PendingSuggestion[] {
  const lastApplied = frontendSettings.lastAppliedSettingsVersion;

  const applicable = registry.filter(
    vs =>
      compareVersions(vs.version, lastApplied) > 0 && compareVersions(vs.version, appVersion) <= 0,
  );

  if (applicable.length === 0)
    return [];

  // Deduplicate by settingType+key — latest version wins
  const byKey = new Map<string, PendingSuggestion>();

  for (const vs of applicable) {
    for (const suggestion of vs.suggestions) {
      const currentValue = getCurrentValue(suggestion, frontendSettings, generalSettings);

      if (suggestion.merge && Array.isArray(currentValue) && Array.isArray(suggestion.suggestedValue)) {
        const missing = suggestion.suggestedValue.filter(v => !currentValue.includes(v));
        if (missing.length === 0)
          continue;

        const merged = [...currentValue, ...missing];
        byKey.set(getSuggestionKey(suggestion), {
          ...suggestion,
          suggestedValue: merged,
          currentValue,
          fromVersion: vs.version,
        } satisfies PendingSuggestion);
      }
      else {
        if (isEqual(currentValue, suggestion.suggestedValue))
          continue;

        byKey.set(getSuggestionKey(suggestion), {
          ...suggestion,
          currentValue,
          fromVersion: vs.version,
        });
      }
    }
  }

  return [...byKey.values()];
}

interface UseSettingsSuggestionsReturn {
  applySelected: (selected: PendingSuggestion[]) => Promise<void>;
  dismissAll: () => Promise<void>;
  checkForSuggestions: (
    frontendSettings: FrontendSettings,
    generalSettings: GeneralSettings,
    newAccount?: boolean,
  ) => Promise<void>;
}

export function useSettingsSuggestions(): UseSettingsSuggestionsReturn {
  const suggestionsStore = useSuggestionsStore();
  const { update, updateFrontendSetting } = useSettingsOperations();
  const { appVersion } = storeToRefs(useMainStore());
  const { t } = useI18n({ useScope: 'global' });

  // Awaited by `initialize` rather than fire-and-forget: `updateFrontendSetting` rewrites the
  // whole settings blob from a snapshot of the repo, so a concurrent write (the privacy reset
  // that follows in `initialize`) would snapshot the pre-stamp version and put it back.
  async function checkForSuggestions(
    frontendSettings: FrontendSettings,
    generalSettings: GeneralSettings,
    newAccount = false,
  ): Promise<void> {
    const version = get(appVersion);
    if (!version || version.includes('dev'))
      return;

    // A freshly created account is already on the current defaults, so recommendations from
    // past versions never apply to it. Stamp the version instead of replaying them — the
    // stored `0.0.0` default would otherwise make every historical suggestion pending, and
    // applying one would move the account *off* the defaults it was just created with.
    if (newAccount) {
      await updateFrontendSetting({ lastAppliedSettingsVersion: version });
      return;
    }

    const registry = createSettingsSuggestions(t);
    const items = collectPendingSuggestions(frontendSettings, generalSettings, version, registry);

    if (items.length > 0) {
      suggestionsStore.pendingSuggestions = items;
      suggestionsStore.showSuggestionsDialog = true;
    }
    else {
      await updateFrontendSetting({ lastAppliedSettingsVersion: version });
    }
  }

  async function applySelected(selected: PendingSuggestion[]): Promise<void> {
    const version = get(appVersion);

    const frontendPayload: FrontendSettingsPayload = {
      lastAppliedSettingsVersion: version,
    };
    const generalPayload: SettingsUpdate = {};

    for (const item of selected) {
      const target = item.settingType === 'frontend' ? frontendPayload : generalPayload;
      Object.assign(target, { [item.key]: item.suggestedValue });
    }

    await updateFrontendSetting(frontendPayload);

    if (Object.keys(generalPayload).length > 0)
      await update(generalPayload);

    suggestionsStore.pendingSuggestions = [];
    suggestionsStore.showSuggestionsDialog = false;
  }

  async function dismissAll(): Promise<void> {
    const version = get(appVersion);
    await updateFrontendSetting({ lastAppliedSettingsVersion: version });
    suggestionsStore.pendingSuggestions = [];
    suggestionsStore.showSuggestionsDialog = false;
  }

  return {
    applySelected,
    checkForSuggestions,
    dismissAll,
  };
}
