import type { GeneralSettings } from '@/types/user';
import { describe, expect, it } from 'vitest';
import { defaultGeneralSettings } from '@/data/factories';
import { Currency } from '@/types/currencies';
import {
  type FrontendSettings,
  getDefaultFrontendSettings,
} from '@/types/settings/frontend-settings';
import { PriceOracle } from '@/types/settings/price-oracle';
import { getSuggestionKey, type VersionSuggestions } from './settings-suggestions';
import { collectPendingSuggestions } from './use-settings-suggestions';

function createFrontendSettings(overrides: Partial<FrontendSettings> = {}): FrontendSettings {
  return getDefaultFrontendSettings(overrides);
}

function createGeneralSettings(overrides: Partial<GeneralSettings> = {}): GeneralSettings {
  return {
    ...defaultGeneralSettings(new Currency('United States Dollar', 'USD', '$')),
    ...overrides,
  };
}

const testRegistry: VersionSuggestions[] = [
  {
    version: '1.42.0',
    suggestions: [
      {
        settingType: 'frontend',
        key: 'itemsPerPage',
        suggestedValue: 25,
        description: 'Increase default items per page to 25',
      },
      {
        settingType: 'frontend',
        key: 'graphZeroBased',
        suggestedValue: true,
        description: 'Enable zero-based graphs',
      },
    ],
  },
  {
    version: '1.43.0',
    suggestions: [
      {
        settingType: 'frontend',
        key: 'itemsPerPage',
        suggestedValue: 50,
        description: 'Increase default items per page to 50',
      },
      {
        settingType: 'general',
        key: 'evmchainsToSkipDetection',
        suggestedValue: ['base', 'polygon_pos'],
        merge: true,
        description: 'Skip detection on Base and Polygon',
      },
    ],
  },
];

describe('getSuggestionKey', () => {
  it('should create unique keys per setting type and key', () => {
    const frontendSuggestion = {
      settingType: 'frontend' as const,
      key: 'itemsPerPage' as const,
      suggestedValue: 25,
      description: 'test',
      currentValue: 10,
      fromVersion: '1.42.0',
    };
    const generalSuggestion = {
      settingType: 'general' as const,
      key: 'evmchainsToSkipDetection' as const,
      suggestedValue: ['base'],
      description: 'test',
      currentValue: [],
      fromVersion: '1.42.0',
    };

    expect(getSuggestionKey(frontendSuggestion)).toBe('frontend:itemsPerPage');
    expect(getSuggestionKey(generalSuggestion)).toBe('general:evmchainsToSkipDetection');
    expect(getSuggestionKey(frontendSuggestion)).not.toBe(getSuggestionKey(generalSuggestion));
  });
});

describe('collectPendingSuggestions', () => {
  it('should return empty array when registry is empty', () => {
    const frontend = createFrontendSettings({ lastAppliedSettingsVersion: '1.41.0' });
    const general = createGeneralSettings();
    const result = collectPendingSuggestions(frontend, general, '1.42.0', []);

    expect(result).toEqual([]);
  });

  it('should return empty array when lastAppliedSettingsVersion matches appVersion', () => {
    const frontend = createFrontendSettings({ lastAppliedSettingsVersion: '1.43.0' });
    const general = createGeneralSettings();
    const result = collectPendingSuggestions(frontend, general, '1.43.0', testRegistry);

    expect(result).toEqual([]);
  });

  it('should return empty array when no versions are in range', () => {
    const frontend = createFrontendSettings({ lastAppliedSettingsVersion: '1.44.0' });
    const general = createGeneralSettings();
    const result = collectPendingSuggestions(frontend, general, '1.45.0', testRegistry);

    expect(result).toEqual([]);
  });

  it('should collect frontend suggestions from a single version', () => {
    const frontend = createFrontendSettings({ lastAppliedSettingsVersion: '1.41.0' });
    const general = createGeneralSettings();
    const result = collectPendingSuggestions(frontend, general, '1.42.0', testRegistry);

    expect(result).toHaveLength(2);
    expect(result[0].key).toBe('itemsPerPage');
    expect(result[0].suggestedValue).toBe(25);
    expect(result[0].fromVersion).toBe('1.42.0');

    expect(result[1].key).toBe('graphZeroBased');
    expect(result[1].suggestedValue).toBe(true);
  });

  it('should merge array values when merge is true', () => {
    const frontend = createFrontendSettings({ lastAppliedSettingsVersion: '1.42.0' });
    const general = createGeneralSettings({ evmchainsToSkipDetection: ['ethereum'] });
    const result = collectPendingSuggestions(frontend, general, '1.43.0', testRegistry);

    const skipDetection = result.find(s => s.key === 'evmchainsToSkipDetection');
    expect(skipDetection).toBeDefined();
    expect(skipDetection?.settingType).toBe('general');
    // Should merge: existing ['ethereum'] + missing ['base', 'polygon_pos']
    expect(skipDetection?.suggestedValue).toEqual(['ethereum', 'base', 'polygon_pos']);
    expect(skipDetection?.currentValue).toEqual(['ethereum']);
  });

  it('should skip merge suggestion when all items already present', () => {
    const frontend = createFrontendSettings({ lastAppliedSettingsVersion: '1.42.0' });
    const general = createGeneralSettings({ evmchainsToSkipDetection: ['base', 'polygon_pos', 'gnosis'] });
    const result = collectPendingSuggestions(frontend, general, '1.43.0', testRegistry);

    const skipDetection = result.find(s => s.key === 'evmchainsToSkipDetection');
    expect(skipDetection).toBeUndefined();
  });

  it('should only add missing items in merge mode', () => {
    const frontend = createFrontendSettings({ lastAppliedSettingsVersion: '1.42.0' });
    const general = createGeneralSettings({ evmchainsToSkipDetection: ['base', 'optimism'] });
    const result = collectPendingSuggestions(frontend, general, '1.43.0', testRegistry);

    const skipDetection = result.find(s => s.key === 'evmchainsToSkipDetection');
    expect(skipDetection).toBeDefined();
    // Only polygon_pos is missing, base is already there
    expect(skipDetection?.suggestedValue).toEqual(['base', 'optimism', 'polygon_pos']);
  });

  it('should filter out suggestions where current value already matches suggested', () => {
    const frontend = createFrontendSettings({
      lastAppliedSettingsVersion: '1.41.0',
      itemsPerPage: 25,
    });
    const general = createGeneralSettings();
    const result = collectPendingSuggestions(frontend, general, '1.42.0', testRegistry);

    expect(result).toHaveLength(1);
    expect(result[0].key).toBe('graphZeroBased');
  });

  it('should handle version jumps and collect from multiple versions', () => {
    const frontend = createFrontendSettings({ lastAppliedSettingsVersion: '1.41.0' });
    const general = createGeneralSettings();
    const result = collectPendingSuggestions(frontend, general, '1.43.0', testRegistry);

    // itemsPerPage appears in both 1.42 and 1.43 — latest wins (50)
    // graphZeroBased from 1.42
    // evmchainsToSkipDetection from 1.43
    expect(result).toHaveLength(3);

    const itemsPerPage = result.find(s => s.key === 'itemsPerPage');
    expect(itemsPerPage?.suggestedValue).toBe(50);
    expect(itemsPerPage?.fromVersion).toBe('1.43.0');

    const graphZeroBased = result.find(s => s.key === 'graphZeroBased');
    expect(graphZeroBased?.suggestedValue).toBe(true);
    expect(graphZeroBased?.fromVersion).toBe('1.42.0');

    const skipDetection = result.find(s => s.key === 'evmchainsToSkipDetection');
    expect(skipDetection?.fromVersion).toBe('1.43.0');
  });

  it('should deduplicate by key with latest version winning', () => {
    const frontend = createFrontendSettings({ lastAppliedSettingsVersion: '1.41.0' });
    const general = createGeneralSettings();
    const result = collectPendingSuggestions(frontend, general, '1.43.0', testRegistry);

    const itemsPerPage = result.filter(s => s.key === 'itemsPerPage');
    expect(itemsPerPage).toHaveLength(1);
    expect(itemsPerPage[0].suggestedValue).toBe(50);
    expect(itemsPerPage[0].fromVersion).toBe('1.43.0');
  });

  it('should include current value in pending suggestions', () => {
    const frontend = createFrontendSettings({
      lastAppliedSettingsVersion: '1.41.0',
      itemsPerPage: 10,
    });
    const general = createGeneralSettings();
    const result = collectPendingSuggestions(frontend, general, '1.42.0', testRegistry);

    const itemsPerPage = result.find(s => s.key === 'itemsPerPage');
    expect(itemsPerPage?.currentValue).toBe(10);
  });

  it('should return empty when all suggestions already match current values', () => {
    const frontend = createFrontendSettings({
      lastAppliedSettingsVersion: '1.41.0',
      itemsPerPage: 25,
      graphZeroBased: true,
    });
    const general = createGeneralSettings();
    const result = collectPendingSuggestions(frontend, general, '1.42.0', testRegistry);

    expect(result).toEqual([]);
  });

  it('should handle default lastAppliedSettingsVersion of 0.0.0', () => {
    const frontend = createFrontendSettings();
    const general = createGeneralSettings();
    const result = collectPendingSuggestions(frontend, general, '1.43.0', testRegistry);

    expect(result.length).toBeGreaterThan(0);
    expect(result.some(s => s.fromVersion === '1.42.0')).toBe(true);
    expect(result.some(s => s.fromVersion === '1.43.0')).toBe(true);
  });

  it('should use deep equality for array values', () => {
    const oracleRegistry: VersionSuggestions[] = [
      {
        version: '1.43.0',
        suggestions: [
          {
            settingType: 'general',
            key: 'currentPriceOracles',
            suggestedValue: [PriceOracle.DEFILLAMA, PriceOracle.COINGECKO],
            description: 'Prioritize DefiLlama',
          },
        ],
      },
    ];

    const frontend = createFrontendSettings({ lastAppliedSettingsVersion: '1.42.0' });

    // When current value matches — should not suggest
    const generalMatching = createGeneralSettings({
      currentPriceOracles: [PriceOracle.DEFILLAMA, PriceOracle.COINGECKO],
    });
    const resultMatching = collectPendingSuggestions(
      frontend,
      generalMatching,
      '1.43.0',
      oracleRegistry,
    );
    expect(resultMatching).toHaveLength(0);

    // When current value differs — should suggest
    const generalDifferent = createGeneralSettings({
      currentPriceOracles: [PriceOracle.COINGECKO, PriceOracle.DEFILLAMA],
    });
    const resultDifferent = collectPendingSuggestions(
      frontend,
      generalDifferent,
      '1.43.0',
      oracleRegistry,
    );
    expect(resultDifferent).toHaveLength(1);
  });
});
