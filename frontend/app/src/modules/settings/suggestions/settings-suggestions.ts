import type { ComposerTranslation } from 'vue-i18n';
import type { FrontendSettings } from '@/modules/settings/types/frontend-settings';
import type { GeneralSettings } from '@/modules/settings/types/user-settings';
import { Blockchain } from '@rotki/common';
import { PriceOracle } from '@/modules/settings/types/price-oracle';

interface BaseSuggestion {
  description: string;
  /**
   * When true for array values, the suggestedValue items are merged into the
   * current value rather than replacing it entirely.
   */
  merge?: boolean;
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

export function createSettingsSuggestions(t: ComposerTranslation): VersionSuggestions[] {
  return [
    {
      version: '1.43.0',
      suggestions: [
        {
          settingType: 'general',
          key: 'evmchainsToSkipDetection',
          suggestedValue: [Blockchain.BASE, Blockchain.POLYGON_POS, Blockchain.GNOSIS],
          merge: true,
          description: t('settings_suggestions.evm_chains_skip_detection_v1_43'),
        },
        {
          settingType: 'general',
          key: 'currentPriceOracles',
          suggestedValue: [
            PriceOracle.DEFILLAMA,
            PriceOracle.COINGECKO,
            PriceOracle.CRYPTOCOMPARE,
            PriceOracle.UNISWAP2,
            PriceOracle.UNISWAP3,
          ],
          description: t('settings_suggestions.current_price_oracles_v1_43'),
        },
        {
          settingType: 'general',
          key: 'historicalPriceOracles',
          suggestedValue: [
            PriceOracle.DEFILLAMA,
            PriceOracle.CRYPTOCOMPARE,
            PriceOracle.COINGECKO,
            PriceOracle.UNISWAP3,
            PriceOracle.UNISWAP2,
          ],
          description: t('settings_suggestions.historical_price_oracles_v1_43'),
        },
      ],
    },
  ];
}
