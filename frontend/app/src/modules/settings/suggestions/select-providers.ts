import type { SuggestionProvider, SuggestionState } from './settings-suggestions';
import { compareVersions } from './compare-versions';

/**
 * Decides which providers are worth resolving, and is the only thing standing between a login and
 * the requests `resolve` may make. A provider survives when its version has shipped, it is not
 * already retired, and its own free precondition passes.
 *
 * What retires it depends on what it is. A value nudge retires once the version cursor passes it:
 * it has had its one release to be offered. A *decision* (`decisionId`) retires only once the user
 * has actually answered it, so closing the dialog does not silently drop the question.
 *
 * Keeping this separate from `collectPendingSuggestions` is the point: that one shapes values and
 * runs on already-built suggestions, while this one runs *before* anything is built, so a question
 * the user has already answered costs nothing to skip.
 */
export function selectProviders(
  providers: SuggestionProvider[],
  state: SuggestionState,
  appVersion: string,
): SuggestionProvider[] {
  const { answeredSuggestions, lastAppliedSettingsVersion } = state.frontend;

  function isRetired(provider: SuggestionProvider): boolean {
    if (provider.decisionId !== undefined)
      return answeredSuggestions.includes(provider.decisionId);
    return compareVersions(provider.version, lastAppliedSettingsVersion) <= 0;
  }

  return providers.filter(provider => (
    compareVersions(provider.version, appVersion) <= 0
    && !isRetired(provider)
    && (provider.isRelevant === undefined || provider.isRelevant(state))
  ));
}
