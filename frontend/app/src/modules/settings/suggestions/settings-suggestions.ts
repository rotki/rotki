import type { ExternalServiceKeys, ExternalServiceName } from '@/modules/integrations/types';
import type { FrontendSettings } from '@/modules/settings/types/frontend-settings';
import type { GeneralSettings } from '@/modules/settings/types/user-settings';
import { Blockchain } from '@rotki/common';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import { gnosisIndexerProvider } from './gnosis-indexer-suggestion';

/** The part of `ComposerTranslation` a suggestion builder needs to label itself. */
export type SuggestionTranslate = (key: string, named?: Record<string, unknown>) => string;

/**
 * One of the mutually exclusive values a choice suggestion offers. The value is only ever handed
 * back to the settings update, so it is deliberately untyped here — the builder that creates the
 * choices is the one place that knows the setting it belongs to.
 */
export interface SuggestionChoice {
  id: string;
  label: string;
  value: unknown;
}

/** A prerequisite for a suggestion that the user either already meets or does not. */
export interface SuggestionRequirement {
  label: string;
  met: boolean;
}

/** Button that takes the user to the api key page of the service a suggestion depends on. */
export interface SuggestionAction {
  label: string;
  service: ExternalServiceName;
}

interface BaseSuggestion {
  description: string;
  /**
   * Marks the row as a one-off question rather than a version-scoped nudge. Set from the provider,
   * and recorded in `answeredSuggestions` once the user has answered it either way.
   */
  decisionId?: string;
  /**
   * When true for array values, the suggestedValue items are merged into the
   * current value rather than replacing it entirely.
   */
  merge?: boolean;
  /** Extra explanation rendered under the description. */
  note?: string;
  /** Listed above the choices so the user can see what their keys already cover. */
  requirements?: SuggestionRequirement[];
  /**
   * Turns the row into a decision: the user picks one of these instead of accepting a single
   * value. A choice is always shown, since the point is the decision itself and not a value that
   * happens to differ from the current one.
   */
  choices?: SuggestionChoice[];
  /** Id of the choice preselected for this user. Only meaningful together with `choices`. */
  recommendedChoice?: string;
  action?: SuggestionAction;
}

export interface FrontendSettingsSuggestion extends BaseSuggestion {
  settingType: 'frontend';
  key: keyof FrontendSettings;
  suggestedValue: FrontendSettings[keyof FrontendSettings];
}

export interface GeneralSettingsSuggestion extends BaseSuggestion {
  settingType: 'general';
  key: keyof GeneralSettings;
  suggestedValue: GeneralSettings[keyof GeneralSettings];
}

export type SettingsSuggestion = FrontendSettingsSuggestion | GeneralSettingsSuggestion;

export interface VersionSuggestions {
  version: string;
  suggestions: SettingsSuggestion[];
}

interface PendingFields {
  currentValue: unknown;
  fromVersion: string;
}

export type PendingSuggestion =
  | (FrontendSettingsSuggestion & PendingFields)
  | (GeneralSettingsSuggestion & PendingFields);

export function getSuggestionKey(suggestion: SettingsSuggestion | PendingSuggestion): string {
  return `${suggestion.settingType}:${suggestion.key}`;
}

/** The settings a provider may read synchronously to decide whether it has anything to ask. */
export interface SuggestionState {
  frontend: FrontendSettings;
  general: GeneralSettings;
}

/**
 * The lookups a provider may need that the settings cannot answer. Injected rather than imported
 * so providers stay unit-testable without mocking api modules, and memoized per run so two
 * providers wanting the same answer cost one request between them.
 */
export interface SuggestionProbes {
  /** Whether the user has any history event for a location. One row is enough to answer it. */
  hasEvents: (location: string) => Promise<boolean>;
  apiKeys: () => Promise<ExternalServiceKeys | undefined>;
}

/**
 * One suggestion, declared with everything needed to decide whether it is worth building.
 *
 * `resolve` may cost network requests, which is why it sits behind two gates it cannot skip: the
 * version must still be pending, and `isRelevant` must pass. Anything free belongs in
 * `isRelevant` so the expensive half never runs for a user it cannot apply to.
 */
export interface SuggestionProvider {
  version: string;
  /**
   * Present when this provider asks a question rather than nudging a value. It then retires on being
   * answered instead of on the version cursor passing `version`, so someone who closes the dialog
   * without deciding is asked again next login.
   */
  decisionId?: string;
  isRelevant?: (state: SuggestionState) => boolean;
  resolve: (
    state: SuggestionState,
    probes: SuggestionProbes,
    t: SuggestionTranslate,
  ) => SettingsSuggestion | undefined | Promise<SettingsSuggestion | undefined>;
}

export const SUGGESTION_PROVIDERS: SuggestionProvider[] = [
  {
    version: '1.43.0',
    resolve: (_state, _probes, t) => ({
      settingType: 'general',
      key: 'evmchainsToSkipDetection',
      suggestedValue: [Blockchain.BASE, Blockchain.POLYGON_POS, Blockchain.GNOSIS],
      merge: true,
      description: t('settings_suggestions.evm_chains_skip_detection_v1_43'),
    }),
  },
  {
    version: '1.43.0',
    resolve: (_state, _probes, t) => ({
      settingType: 'general',
      key: 'currentPriceOracles',
      suggestedValue: [
        PriceOracle.DEFILLAMA,
        PriceOracle.COINGECKO,
        PriceOracle.UNISWAP2,
        PriceOracle.UNISWAP3,
      ],
      description: t('settings_suggestions.current_price_oracles_v1_43'),
    }),
  },
  {
    version: '1.43.0',
    resolve: (_state, _probes, t) => ({
      settingType: 'general',
      key: 'historicalPriceOracles',
      suggestedValue: [
        PriceOracle.DEFILLAMA,
        PriceOracle.COINGECKO,
        PriceOracle.UNISWAP3,
        PriceOracle.UNISWAP2,
      ],
      description: t('settings_suggestions.historical_price_oracles_v1_43'),
    }),
  },
  gnosisIndexerProvider,
];
