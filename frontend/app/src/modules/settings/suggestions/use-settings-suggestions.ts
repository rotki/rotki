import type { ExternalServiceKeys } from '@/modules/integrations/types';
import type { FrontendSettings, FrontendSettingsPayload } from '@/modules/settings/types/frontend-settings';
import type { GeneralSettings, SettingsUpdate } from '@/modules/settings/types/user-settings';
import { Blockchain } from '@rotki/common';
import { isEqual } from 'es-toolkit';
import { logger } from '@/modules/core/common/logging/logging';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useExternalServicesApi } from '@/modules/settings/api/use-external-services-api';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { compareVersions } from './compare-versions';
import { type GnosisIndexerContext, hasCustomGnosisOrder } from './gnosis-indexer-suggestion';
import {
  createSettingsSuggestions,
  getSuggestionKey,
  type PendingSuggestion,
  type SettingsSuggestion,
  type SuggestionContext,
  type VersionSuggestions,
} from './settings-suggestions';
import { useSuggestionsStore } from './use-suggestions-store';

/** What the dialog hands back: the accepted rows plus the choice picked for each choice row. */
export interface SuggestionSelection {
  selected: PendingSuggestion[];
  choices: Record<string, string>;
}

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

      if (suggestion.choices) {
        // A choice asks the user to decide, so it stands even when one of its options is what
        // they already have. Its builder is the one that decides whether to offer it at all.
        byKey.set(getSuggestionKey(suggestion), {
          ...suggestion,
          currentValue,
          fromVersion: vs.version,
        });
      }
      else if (suggestion.merge && Array.isArray(currentValue) && Array.isArray(suggestion.suggestedValue)) {
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
  applySelected: (selection: SuggestionSelection) => Promise<void>;
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
  const { fetchHistoryEvents } = useHistoryEventsApi();
  const { queryExternalServices } = useExternalServicesApi();
  const { t } = useI18n({ useScope: 'global' });

  /** A single row is all it takes to answer "has this user ever had gnosis activity". */
  async function queryHasGnosisEvents(): Promise<boolean> {
    try {
      const { entriesFound } = await fetchHistoryEvents({
        aggregateByGroupIds: false,
        limit: 1,
        location: Blockchain.GNOSIS,
        offset: 0,
      });
      return entriesFound > 0;
    }
    catch (error: unknown) {
      logger.error(error);
      return false;
    }
  }

  async function queryApiKeys(): Promise<ExternalServiceKeys | undefined> {
    try {
      return await queryExternalServices();
    }
    catch (error: unknown) {
      logger.error(error);
      return undefined;
    }
  }

  /**
   * Both probes below cost a request at login, so only the users the gnosis question can apply to
   * pay for them: an untouched or already default gnosis order needs no decision.
   */
  async function buildContext(generalSettings: GeneralSettings): Promise<SuggestionContext> {
    const indexersOrder = generalSettings.evmIndexersOrder;
    const inactive: GnosisIndexerContext = {
      hasBlockscoutKey: false,
      hasEtherscanKey: false,
      hasGnosisEvents: false,
      indexersOrder,
    };

    if (!hasCustomGnosisOrder(indexersOrder) || !await queryHasGnosisEvents())
      return { gnosisIndexer: inactive };

    const keys = await queryApiKeys();
    return {
      gnosisIndexer: {
        hasBlockscoutKey: !!keys?.blockscout?.apiKey,
        hasEtherscanKey: !!keys?.etherscan?.apiKey,
        hasGnosisEvents: true,
        indexersOrder,
      },
    };
  }

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

    const registry = createSettingsSuggestions(t, await buildContext(generalSettings));
    const items = collectPendingSuggestions(frontendSettings, generalSettings, version, registry);

    if (items.length > 0) {
      suggestionsStore.pendingSuggestions = items;
      suggestionsStore.showSuggestionsDialog = true;
    }
    else {
      await updateFrontendSetting({ lastAppliedSettingsVersion: version });
    }
  }

  async function applySelected({ choices, selected }: SuggestionSelection): Promise<void> {
    const version = get(appVersion);

    const frontendPayload: FrontendSettingsPayload = {
      lastAppliedSettingsVersion: version,
    };
    const generalPayload: SettingsUpdate = {};

    for (const item of selected) {
      const target = item.settingType === 'frontend' ? frontendPayload : generalPayload;
      const chosen = item.choices?.find(choice => choice.id === choices[getSuggestionKey(item)]);
      Object.assign(target, { [item.key]: chosen ? chosen.value : item.suggestedValue });
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
