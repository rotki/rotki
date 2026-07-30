import type { SuggestionProbes, SuggestionState } from './settings-suggestions';
import type { GeneralSettings } from '@/modules/settings/types/user-settings';
import { describe, expect, it, vi } from 'vitest';
import { Currency } from '@/modules/assets/amount-display/currencies';
import { defaultGeneralSettings } from '@/modules/settings/factories';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';
import { getDefaultFrontendSettings } from '@/modules/settings/types/frontend-settings';
import {
  BLOCKSCOUT_FIRST_GNOSIS_ORDER,
  createGnosisIndexerSuggestion,
  ETHERSCAN_FIRST_GNOSIS_ORDER,
  type GnosisIndexerContext,
  gnosisIndexerProvider,
  hasCustomGnosisOrder,
} from './gnosis-indexer-suggestion';

function createGeneralSettings(overrides: Partial<GeneralSettings> = {}): GeneralSettings {
  return {
    ...defaultGeneralSettings(new Currency('United States Dollar', 'USD', '$')),
    ...overrides,
  };
}

const t = (key: string): string => key;

function createContext(overrides: Partial<GnosisIndexerContext> = {}): GnosisIndexerContext {
  return {
    hasBlockscoutKey: false,
    hasEtherscanKey: false,
    indexersOrder: { gnosis: [EvmIndexer.ETHERSCAN] },
    ...overrides,
  };
}

describe('hasCustomGnosisOrder', () => {
  it('should be false when gnosis has no order of its own', () => {
    expect(hasCustomGnosisOrder({ optimism: [EvmIndexer.ETHERSCAN] })).toBe(false);
  });

  it('should be false when the gnosis order is the new default', () => {
    expect(hasCustomGnosisOrder({ gnosis: [...BLOCKSCOUT_FIRST_GNOSIS_ORDER] })).toBe(false);
  });

  it('should be true for any other explicit gnosis order', () => {
    expect(hasCustomGnosisOrder({ gnosis: [EvmIndexer.ETHERSCAN] })).toBe(true);
    expect(hasCustomGnosisOrder({ gnosis: [...ETHERSCAN_FIRST_GNOSIS_ORDER] })).toBe(true);
  });
});

describe('createGnosisIndexerSuggestion', () => {
  it('should not ask users who never customized the gnosis order', () => {
    expect(createGnosisIndexerSuggestion(t, createContext({ indexersOrder: {} }))).toBeUndefined();
  });

  it('should offer both orders and keep the other chains untouched', () => {
    const suggestion = createGnosisIndexerSuggestion(t, createContext({
      indexersOrder: { gnosis: [EvmIndexer.ETHERSCAN], optimism: [EvmIndexer.ROUTESCAN] },
    }));

    expect(suggestion?.key).toBe('evmIndexersOrder');
    expect(suggestion?.choices).toEqual([
      expect.objectContaining({
        id: EvmIndexer.BLOCKSCOUT,
        value: { gnosis: BLOCKSCOUT_FIRST_GNOSIS_ORDER, optimism: [EvmIndexer.ROUTESCAN] },
      }),
      expect.objectContaining({
        id: EvmIndexer.ETHERSCAN,
        value: { gnosis: ETHERSCAN_FIRST_GNOSIS_ORDER, optimism: [EvmIndexer.ROUTESCAN] },
      }),
    ]);
  });

  it('should recommend blockscout when its key is set', () => {
    const suggestion = createGnosisIndexerSuggestion(t, createContext({
      hasBlockscoutKey: true,
      hasEtherscanKey: true,
    }));

    expect(suggestion?.recommendedChoice).toBe(EvmIndexer.BLOCKSCOUT);
    expect(suggestion?.suggestedValue).toEqual({ gnosis: BLOCKSCOUT_FIRST_GNOSIS_ORDER });
    expect(suggestion?.action).toBeUndefined();
  });

  it('should recommend etherscan when only its key is set', () => {
    const suggestion = createGnosisIndexerSuggestion(t, createContext({ hasEtherscanKey: true }));

    expect(suggestion?.recommendedChoice).toBe(EvmIndexer.ETHERSCAN);
    expect(suggestion?.suggestedValue).toEqual({ gnosis: ETHERSCAN_FIRST_GNOSIS_ORDER });
  });

  it('should still offer the blockscout key when only an etherscan key is set', () => {
    // That key may well be a free one, which no longer serves gnosis, and nothing here can tell.
    const suggestion = createGnosisIndexerSuggestion(t, createContext({ hasEtherscanKey: true }));

    expect(suggestion?.action?.service).toBe('blockscout');
  });

  it('should recommend blockscout and link to its key when neither key is set', () => {
    const suggestion = createGnosisIndexerSuggestion(t, createContext());

    expect(suggestion?.recommendedChoice).toBe(EvmIndexer.BLOCKSCOUT);
    expect(suggestion?.action?.service).toBe('blockscout');
    expect(suggestion?.requirements).toEqual([
      expect.objectContaining({ met: false }),
      expect.objectContaining({ met: false }),
    ]);
  });

  it('should recommend blockscout when only its key is set', () => {
    const suggestion = createGnosisIndexerSuggestion(t, createContext({ hasBlockscoutKey: true }));

    expect(suggestion?.recommendedChoice).toBe(EvmIndexer.BLOCKSCOUT);
    expect(suggestion?.action).toBeUndefined();
  });
});

describe('gnosisIndexerProvider', () => {
  function createProbes(overrides: Partial<SuggestionProbes> = {}): SuggestionProbes {
    return {
      apiKeys: vi.fn(async () => ({ blockscout: { apiKey: 'key' } })),
      hasEvents: vi.fn(async () => true),
      ...overrides,
    };
  }

  function createState(indexersOrder: GeneralSettings['evmIndexersOrder']): SuggestionState {
    return {
      frontend: getDefaultFrontendSettings(),
      general: createGeneralSettings({ evmIndexersOrder: indexersOrder }),
    };
  }

  it('should be irrelevant when the gnosis order is untouched', () => {
    const state = createState({ optimism: [EvmIndexer.ETHERSCAN] });

    expect(gnosisIndexerProvider.isRelevant?.(state)).toBe(false);
  });

  it('should be relevant when the user picked their own gnosis order', () => {
    const state = createState({ gnosis: [EvmIndexer.ETHERSCAN] });

    expect(gnosisIndexerProvider.isRelevant?.(state)).toBe(true);
  });

  it('should not look up api keys for a user with no gnosis events', async () => {
    const probes = createProbes({ hasEvents: vi.fn(async () => false) });

    const suggestion = await gnosisIndexerProvider.resolve(
      createState({ gnosis: [EvmIndexer.ETHERSCAN] }),
      probes,
      t,
    );

    expect(suggestion).toBeUndefined();
    expect(probes.apiKeys).not.toHaveBeenCalled();
  });

  it('should build the row from the keys the probes report', async () => {
    const probes = createProbes({ apiKeys: vi.fn(async () => ({ etherscan: { apiKey: 'key' } })) });

    const suggestion = await gnosisIndexerProvider.resolve(
      createState({ gnosis: [EvmIndexer.ETHERSCAN] }),
      probes,
      t,
    );

    expect(probes.hasEvents).toHaveBeenCalledWith('gnosis');
    expect(suggestion?.recommendedChoice).toBe(EvmIndexer.ETHERSCAN);
    expect(suggestion?.requirements).toEqual([
      expect.objectContaining({ met: false }),
      expect.objectContaining({ met: true }),
    ]);
  });
});
