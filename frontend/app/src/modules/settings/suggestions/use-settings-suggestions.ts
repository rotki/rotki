import type { FrontendSettings, FrontendSettingsPayload } from '@/modules/settings/types/frontend-settings';
import type { GeneralSettings, SettingsUpdate } from '@/modules/settings/types/user-settings';
import { isEqual } from 'es-toolkit';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { compareVersions } from './compare-versions';
import { selectProviders } from './select-providers';
import {
  getSuggestionKey,
  type PendingSuggestion,
  type SettingsSuggestion,
  SUGGESTION_PROVIDERS,
  type SuggestionProvider,
  type SuggestionState,
  type VersionSuggestions,
} from './settings-suggestions';
import { useSuggestionProbes } from './use-suggestion-probes';
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
 * Turns one suggestion into the row the dialog shows, or nothing when this user has no reason to see
 * it. The three shapes differ in what "already satisfied" means for them.
 */
function shapePending(
  suggestion: SettingsSuggestion,
  currentValue: unknown,
  fromVersion: string,
): PendingSuggestion | undefined {
  // A choice asks the user to decide, so it stands even when one of its options is what they
  // already have. Its builder is the one that decides whether to offer it at all.
  if (suggestion.choices)
    return { ...suggestion, currentValue, fromVersion };

  if (suggestion.merge && Array.isArray(currentValue) && Array.isArray(suggestion.suggestedValue)) {
    const missing = suggestion.suggestedValue.filter(v => !currentValue.includes(v));
    if (missing.length === 0)
      return undefined;

    return {
      ...suggestion,
      suggestedValue: [...currentValue, ...missing],
      currentValue,
      fromVersion,
    } satisfies PendingSuggestion;
  }

  if (isEqual(currentValue, suggestion.suggestedValue))
    return undefined;

  return { ...suggestion, currentValue, fromVersion };
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

  // Deduplicate by settingType+key — latest version wins
  const byKey = new Map<string, PendingSuggestion>();

  for (const vs of registry) {
    const versionPending
      = compareVersions(vs.version, lastApplied) > 0 && compareVersions(vs.version, appVersion) <= 0;

    for (const suggestion of vs.suggestions) {
      // A decision is retired by being answered, not by the version cursor, so the window that
      // scopes a value nudge to its release does not apply to it.
      if (!versionPending && suggestion.decisionId === undefined)
        continue;

      const currentValue = getCurrentValue(suggestion, frontendSettings, generalSettings);
      const pending = shapePending(suggestion, currentValue, vs.version);
      if (pending)
        byKey.set(getSuggestionKey(suggestion), pending);
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

/**
 * @param providers the registry to consider. Injected rather than imported so a spec can hand in the
 * providers it is about instead of mocking the module the rest of the pipeline is typed against.
 */
export function useSettingsSuggestions(
  providers: SuggestionProvider[] = SUGGESTION_PROVIDERS,
): UseSettingsSuggestionsReturn {
  const suggestionsStore = useSuggestionsStore();
  const repo = useSettingsRepo();
  const { logged } = storeToRefs(useSessionAuthStore());
  const { update, updateFrontendSetting } = useSettingsOperations();
  const { appVersion } = storeToRefs(useMainStore());
  const { createProbes } = useSuggestionProbes();
  const { t } = useI18n({ useScope: 'global' });

  /**
   * Build only what survived the gate. Providers resolve concurrently and share one memoized probe
   * set, so two of them wanting the same lookup cost one request between them.
   *
   * `settled` names the decisions that ran and found they do not apply to this user. They are not
   * going to be asked, and without recording that they would be re-probed on every login forever,
   * since only an answer retires a decision. A run where a probe failed settles nothing: "I could
   * not find out" must not be mistaken for "no".
   */
  async function resolveRegistry(
    state: SuggestionState,
  ): Promise<{ registry: VersionSuggestions[]; settled: string[] }> {
    const selected = selectProviders(providers, state, get(appVersion));
    if (selected.length === 0)
      return { registry: [], settled: [] };

    const { failed, probes } = createProbes();
    const resolved = await Promise.all(selected.map(async provider => ({
      decisionId: provider.decisionId,
      suggestion: await provider.resolve(state, probes, t),
      version: provider.version,
    })));

    const settled = failed()
      ? []
      : resolved.flatMap(({ decisionId, suggestion }) => decisionId !== undefined && !suggestion ? [decisionId] : []);

    const byVersion = new Map<string, SettingsSuggestion[]>();
    for (const { decisionId, suggestion, version } of resolved) {
      if (!suggestion)
        continue;

      // Stamped here rather than in the builder: whether a row is a decision is the registry's call,
      // and this is what carries it through to `applySelected` so the answer can be recorded.
      const stamped = decisionId === undefined ? suggestion : { ...suggestion, decisionId };

      const existing = byVersion.get(version);
      if (existing)
        existing.push(stamped);
      else
        byVersion.set(version, [stamped]);
    }

    return { registry: Array.from(byVersion, ([version, suggestions]) => ({ suggestions, version })), settled };
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
    //
    // Decisions have to be retired by id here as well, not just by the version stamp: they
    // survive the version cursor by design, so stamping alone would let one resurface the moment
    // the account happens to land in the state the question looks for. Someone who deliberately
    // picks an etherscan-first gnosis order on a new 1.44 account has not upgraded into the
    // problem the question is about — they have answered it in advance.
    if (newAccount) {
      const answeredSuggestions = mergeAnswered(
        providers.flatMap(provider => provider.decisionId !== undefined ? [provider.decisionId] : []),
      );
      await updateFrontendSetting({
        lastAppliedSettingsVersion: version,
        ...(answeredSuggestions ? { answeredSuggestions } : {}),
      });
      return;
    }

    const { registry, settled } = await resolveRegistry({ frontend: frontendSettings, general: generalSettings });

    // The probes above are network calls, so the user may well have logged out while they were in
    // flight. Writing here regardless would show one account's suggestions to the next one to log
    // in, and apply them to that account's settings.
    if (!get(logged))
      return;

    const items = collectPendingSuggestions(frontendSettings, generalSettings, version, registry);

    if (items.length > 0) {
      suggestionsStore.pendingSuggestions = items;
      suggestionsStore.showSuggestionsDialog = true;
    }
    else {
      const answeredSuggestions = mergeAnswered(settled);
      await updateFrontendSetting({
        lastAppliedSettingsVersion: version,
        ...(answeredSuggestions ? { answeredSuggestions } : {}),
      });
    }
  }

  /** The stored answers plus `ids`, or nothing when they add none — so no pointless write happens. */
  function mergeAnswered(ids: string[]): string[] | undefined {
    const answered = repo.frontend.answeredSuggestions;
    const fresh = [...new Set(ids)].filter(id => !answered.includes(id));

    return fresh.length > 0 ? [...answered, ...fresh] : undefined;
  }

  /**
   * The decisions the user just answered, merged into what they had answered before.
   *
   * Every decision that was *shown* counts as answered, whether it was accepted, left unchecked, or
   * declined outright. Picking "keep what I have" is an answer, and the ongoing "you may be broken"
   * warning is the missing-api-key notification's job, not this dialog's.
   */
  function recordAnswers(shown: readonly PendingSuggestion[]): string[] | undefined {
    return mergeAnswered(shown.flatMap(item => item.decisionId !== undefined ? [item.decisionId] : []));
  }

  async function applySelected({ choices, selected }: SuggestionSelection): Promise<void> {
    const version = get(appVersion);
    const answeredSuggestions = recordAnswers(suggestionsStore.pendingSuggestions);

    const frontendPayload: FrontendSettingsPayload = {
      lastAppliedSettingsVersion: version,
      ...(answeredSuggestions ? { answeredSuggestions } : {}),
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
    const answeredSuggestions = recordAnswers(suggestionsStore.pendingSuggestions);
    await updateFrontendSetting({
      lastAppliedSettingsVersion: version,
      ...(answeredSuggestions ? { answeredSuggestions } : {}),
    });
    suggestionsStore.pendingSuggestions = [];
    suggestionsStore.showSuggestionsDialog = false;
  }

  return {
    applySelected,
    checkForSuggestions,
    dismissAll,
  };
}
