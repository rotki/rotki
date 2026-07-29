import type { GeneralSettings } from '@/modules/settings/types/user-settings';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Currency } from '@/modules/assets/amount-display/currencies';
import { defaultGeneralSettings } from '@/modules/settings/factories';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';
import {
  type FrontendSettings,
  getDefaultFrontendSettings,
} from '@/modules/settings/types/frontend-settings';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import { getSuggestionKey, type PendingSuggestion, type VersionSuggestions } from './settings-suggestions';
import { collectPendingSuggestions, useSettingsSuggestions } from './use-settings-suggestions';

const { mockRegistry } = vi.hoisted<{ mockRegistry: { value: VersionSuggestions[] } }>(() => ({ mockRegistry: { value: [] } }));
const mockUpdate = vi.fn();
const mockUpdateFrontendSetting = vi.fn();
const mockFetchHistoryEvents = vi.fn();
const mockQueryExternalServices = vi.fn();
const mockAppVersion = ref<string>('1.43.0');
const mockStore: { pendingSuggestions: PendingSuggestion[]; showSuggestionsDialog: boolean } = { pendingSuggestions: [], showSuggestionsDialog: false };

vi.mock('./settings-suggestions', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./settings-suggestions')>();
  return { ...actual, createSettingsSuggestions: vi.fn(() => mockRegistry.value) };
});

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: vi.fn(() => ({
    fetchHistoryEvents: mockFetchHistoryEvents,
  })),
}));

vi.mock('@/modules/settings/api/use-external-services-api', () => ({
  useExternalServicesApi: vi.fn(() => ({
    queryExternalServices: mockQueryExternalServices,
  })),
}));

vi.mock('./use-suggestions-store', () => ({
  useSuggestionsStore: vi.fn(() => mockStore),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: vi.fn(() => ({
    update: mockUpdate,
    updateFrontendSetting: mockUpdateFrontendSetting,
  })),
}));

vi.mock('@/modules/core/common/use-main-store', () => ({
  useMainStore: vi.fn(() => ({
    appVersion: mockAppVersion,
  })),
}));

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

  it('should keep a choice suggestion even when it matches the current value', () => {
    const choiceRegistry: VersionSuggestions[] = [
      {
        version: '1.44.0',
        suggestions: [
          {
            settingType: 'general',
            key: 'evmIndexersOrder',
            suggestedValue: { gnosis: [EvmIndexer.BLOCKSCOUT] },
            choices: [{ id: 'blockscout', label: 'Blockscout', value: { gnosis: [EvmIndexer.BLOCKSCOUT] } }],
            description: 'Choose the gnosis indexer',
          },
        ],
      },
    ];

    const result = collectPendingSuggestions(
      createFrontendSettings({ lastAppliedSettingsVersion: '1.43.0' }),
      createGeneralSettings({ evmIndexersOrder: { gnosis: [EvmIndexer.BLOCKSCOUT] } }),
      '1.44.0',
      choiceRegistry,
    );

    expect(result).toHaveLength(1);
    expect(result[0].currentValue).toEqual({ gnosis: [EvmIndexer.BLOCKSCOUT] });
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

describe('useSettingsSuggestions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRegistry.value = [];
    set(mockAppVersion, '1.43.0');
    mockStore.pendingSuggestions = [];
    mockStore.showSuggestionsDialog = false;
    mockUpdateFrontendSetting.mockResolvedValue(undefined);
    mockUpdate.mockResolvedValue(undefined);
    mockFetchHistoryEvents.mockResolvedValue({ entriesFound: 0 });
    mockQueryExternalServices.mockResolvedValue({});
  });

  describe('checkForSuggestions', () => {
    it('should do nothing on a development version', async () => {
      set(mockAppVersion, '1.43.0-dev');
      const { checkForSuggestions } = useSettingsSuggestions();
      await checkForSuggestions(createFrontendSettings(), createGeneralSettings());

      expect(mockUpdateFrontendSetting).not.toHaveBeenCalled();
      expect(mockStore.showSuggestionsDialog).toBe(false);
    });

    it('should do nothing when the app version is empty', async () => {
      set(mockAppVersion, '');
      const { checkForSuggestions } = useSettingsSuggestions();
      await checkForSuggestions(createFrontendSettings(), createGeneralSettings());

      expect(mockUpdateFrontendSetting).not.toHaveBeenCalled();
    });

    it('should open the dialog when there are pending suggestions', async () => {
      mockRegistry.value = [
        { suggestions: [{ description: 'd', key: 'submitUsageAnalytics', settingType: 'general', suggestedValue: true }], version: '1.43.0' },
      ];
      const { checkForSuggestions } = useSettingsSuggestions();
      await checkForSuggestions(createFrontendSettings(), createGeneralSettings({ submitUsageAnalytics: false }));

      expect(mockStore.showSuggestionsDialog).toBe(true);
      expect(mockStore.pendingSuggestions).toHaveLength(1);
      expect(mockUpdateFrontendSetting).not.toHaveBeenCalled();
    });

    it('should mark the version applied when there are no suggestions', async () => {
      const { checkForSuggestions } = useSettingsSuggestions();
      await checkForSuggestions(createFrontendSettings(), createGeneralSettings());

      expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({ lastAppliedSettingsVersion: '1.43.0' });
      expect(mockStore.showSuggestionsDialog).toBe(false);
    });

    it('should skip the dialog for a new account and mark the version applied', async () => {
      mockRegistry.value = [
        { suggestions: [{ description: 'd', key: 'submitUsageAnalytics', settingType: 'general', suggestedValue: true }], version: '1.43.0' },
      ];
      const { checkForSuggestions } = useSettingsSuggestions();
      await checkForSuggestions(createFrontendSettings(), createGeneralSettings({ submitUsageAnalytics: false }), true);

      expect(mockStore.showSuggestionsDialog).toBe(false);
      expect(mockStore.pendingSuggestions).toEqual([]);
      expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({ lastAppliedSettingsVersion: '1.43.0' });
    });

    it('should not probe for gnosis activity when the gnosis order is untouched', async () => {
      const { checkForSuggestions } = useSettingsSuggestions();
      await checkForSuggestions(createFrontendSettings(), createGeneralSettings({
        evmIndexersOrder: { gnosis: [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN], optimism: [EvmIndexer.ETHERSCAN] },
      }));

      expect(mockFetchHistoryEvents).not.toHaveBeenCalled();
      expect(mockQueryExternalServices).not.toHaveBeenCalled();
    });

    it('should look up the api keys only once gnosis events are found', async () => {
      const general = createGeneralSettings({ evmIndexersOrder: { gnosis: [EvmIndexer.ETHERSCAN] } });
      const { checkForSuggestions } = useSettingsSuggestions();
      await checkForSuggestions(createFrontendSettings(), general);

      expect(mockFetchHistoryEvents).toHaveBeenCalledWith({
        aggregateByGroupIds: false,
        limit: 1,
        location: 'gnosis',
        offset: 0,
      });
      expect(mockQueryExternalServices).not.toHaveBeenCalled();

      mockFetchHistoryEvents.mockResolvedValue({ entriesFound: 3 });
      await checkForSuggestions(createFrontendSettings(), general);

      expect(mockQueryExternalServices).toHaveBeenCalledOnce();
    });

    it('should treat a failed gnosis probe as no activity', async () => {
      mockFetchHistoryEvents.mockRejectedValue(new Error('offline'));
      const { checkForSuggestions } = useSettingsSuggestions();
      await checkForSuggestions(createFrontendSettings(), createGeneralSettings({
        evmIndexersOrder: { gnosis: [EvmIndexer.ETHERSCAN] },
      }));

      expect(mockQueryExternalServices).not.toHaveBeenCalled();
      expect(mockStore.showSuggestionsDialog).toBe(false);
    });
  });

  describe('applySelected', () => {
    it('should split frontend and general payloads and reset the store', async () => {
      mockStore.showSuggestionsDialog = true;
      const selected: PendingSuggestion[] = [
        { currentValue: false, description: 'd', fromVersion: '1.43.0', key: 'defiSetupDone', settingType: 'frontend', suggestedValue: true },
        { currentValue: 2, description: 'd', fromVersion: '1.43.0', key: 'uiFloatingPrecision', settingType: 'general', suggestedValue: 6 },
      ];

      const { applySelected } = useSettingsSuggestions();
      await applySelected({ choices: {}, selected });

      expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({ defiSetupDone: true, lastAppliedSettingsVersion: '1.43.0' });
      expect(mockUpdate).toHaveBeenCalledWith({ uiFloatingPrecision: 6 });
      expect(mockStore.pendingSuggestions).toEqual([]);
      expect(mockStore.showSuggestionsDialog).toBe(false);
    });

    it('should not call the general update when only frontend settings are selected', async () => {
      const selected: PendingSuggestion[] = [
        { currentValue: false, description: 'd', fromVersion: '1.43.0', key: 'defiSetupDone', settingType: 'frontend', suggestedValue: true },
      ];

      const { applySelected } = useSettingsSuggestions();
      await applySelected({ choices: {}, selected });

      expect(mockUpdateFrontendSetting).toHaveBeenCalledOnce();
      expect(mockUpdate).not.toHaveBeenCalled();
    });

    it('should write the picked choice instead of the recommended value', async () => {
      const selected: PendingSuggestion[] = [{
        choices: [
          { id: 'blockscout', label: 'b', value: { gnosis: [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN] } },
          { id: 'etherscan', label: 'e', value: { gnosis: [EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT] } },
        ],
        currentValue: { gnosis: [EvmIndexer.ETHERSCAN] },
        description: 'd',
        fromVersion: '1.44.0',
        key: 'evmIndexersOrder',
        recommendedChoice: 'blockscout',
        settingType: 'general',
        suggestedValue: { gnosis: [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN] },
      }];

      const { applySelected } = useSettingsSuggestions();
      await applySelected({ choices: { 'general:evmIndexersOrder': 'etherscan' }, selected });

      expect(mockUpdate).toHaveBeenCalledWith({
        evmIndexersOrder: { gnosis: [EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT] },
      });
    });

    it('should fall back to the suggested value when no choice was picked', async () => {
      const selected: PendingSuggestion[] = [{
        choices: [{ id: 'blockscout', label: 'b', value: { gnosis: [EvmIndexer.BLOCKSCOUT] } }],
        currentValue: { gnosis: [EvmIndexer.ETHERSCAN] },
        description: 'd',
        fromVersion: '1.44.0',
        key: 'evmIndexersOrder',
        settingType: 'general',
        suggestedValue: { gnosis: [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN] },
      }];

      const { applySelected } = useSettingsSuggestions();
      await applySelected({ choices: {}, selected });

      expect(mockUpdate).toHaveBeenCalledWith({
        evmIndexersOrder: { gnosis: [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN] },
      });
    });
  });

  describe('dismissAll', () => {
    it('should persist the current version and reset the store', async () => {
      mockStore.pendingSuggestions = [
        { currentValue: false, description: 'd', fromVersion: '1.43.0', key: 'defiSetupDone', settingType: 'frontend', suggestedValue: true },
      ];
      mockStore.showSuggestionsDialog = true;

      const { dismissAll } = useSettingsSuggestions();
      await dismissAll();

      expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({ lastAppliedSettingsVersion: '1.43.0' });
      expect(mockStore.pendingSuggestions).toEqual([]);
      expect(mockStore.showSuggestionsDialog).toBe(false);
    });
  });
});
