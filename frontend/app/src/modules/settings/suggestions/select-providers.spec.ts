import { describe, expect, it, vi } from 'vitest';
import { Currency } from '@/modules/assets/amount-display/currencies';
import { defaultGeneralSettings } from '@/modules/settings/factories';
import { getDefaultFrontendSettings } from '@/modules/settings/types/frontend-settings';
import { selectProviders } from './select-providers';
import {
  type SettingsSuggestion,
  SUGGESTION_PROVIDERS,
  type SuggestionProvider,
  type SuggestionState,
} from './settings-suggestions';

const SUGGESTION: SettingsSuggestion = {
  description: 'd',
  key: 'submitUsageAnalytics',
  settingType: 'general',
  suggestedValue: true,
};

function state(frontend: { answeredSuggestions?: string[]; lastAppliedSettingsVersion?: string } = {}): SuggestionState {
  return {
    frontend: getDefaultFrontendSettings(frontend),
    general: defaultGeneralSettings(new Currency('United States Dollar', 'USD', '$')),
  };
}

function provider(overrides: Partial<SuggestionProvider> = {}): SuggestionProvider {
  return { resolve: () => SUGGESTION, version: '1.44.0', ...overrides };
}

describe('selectProviders', () => {
  it('should skip a provider whose version has not shipped yet', () => {
    expect(selectProviders([provider({ version: '1.45.0' })], state(), '1.44.0')).toEqual([]);
  });

  it('should select a nudge whose version is still pending', () => {
    const pending = provider();
    expect(selectProviders([pending], state({ lastAppliedSettingsVersion: '1.43.0' }), '1.44.0')).toEqual([pending]);
  });

  it('should retire a nudge once the version cursor has passed it', () => {
    const result = selectProviders([provider()], state({ lastAppliedSettingsVersion: '1.44.0' }), '1.44.0');
    expect(result).toEqual([]);
  });

  it('should keep asking a decision the version cursor has passed but nobody answered', () => {
    const decision = provider({ decisionId: 'some-decision' });
    const result = selectProviders([decision], state({ lastAppliedSettingsVersion: '1.44.0' }), '1.44.0');

    expect(result).toEqual([decision]);
  });

  it('should retire a decision once it has been answered', () => {
    const result = selectProviders(
      [provider({ decisionId: 'some-decision' })],
      state({ answeredSuggestions: ['some-decision'], lastAppliedSettingsVersion: '1.43.0' }),
      '1.44.0',
    );

    expect(result).toEqual([]);
  });

  it('should not confuse one answered decision for another', () => {
    const decision = provider({ decisionId: 'wanted' });
    const result = selectProviders(
      [decision],
      state({ answeredSuggestions: ['unrelated'], lastAppliedSettingsVersion: '1.43.0' }),
      '1.44.0',
    );

    expect(result).toEqual([decision]);
  });

  it('should drop a provider whose own precondition fails', () => {
    const result = selectProviders(
      [provider({ isRelevant: () => false })],
      state({ lastAppliedSettingsVersion: '1.43.0' }),
      '1.44.0',
    );

    expect(result).toEqual([]);
  });

  it('should not consult the precondition of an already retired provider', () => {
    const isRelevant = vi.fn(() => true);
    selectProviders([provider({ isRelevant })], state({ lastAppliedSettingsVersion: '1.44.0' }), '1.44.0');

    expect(isRelevant).not.toHaveBeenCalled();
  });

  it('should give every shipped provider a unique decision id', () => {
    const ids = SUGGESTION_PROVIDERS.flatMap(p => p.decisionId ? [p.decisionId] : []);

    // A reused id silently retires someone else's question; a renamed one re-asks everybody who
    // had already answered. Neither is visible without this.
    expect(new Set(ids).size).toBe(ids.length);
  });
});
