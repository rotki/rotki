import { describe, expect, it } from 'vitest';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';
import {
  BLOCKSCOUT_FIRST_GNOSIS_ORDER,
  createGnosisIndexerSuggestion,
  ETHERSCAN_FIRST_GNOSIS_ORDER,
  type GnosisIndexerContext,
  hasCustomGnosisOrder,
} from './gnosis-indexer-suggestion';

const t = (key: string): string => key;

function createContext(overrides: Partial<GnosisIndexerContext> = {}): GnosisIndexerContext {
  return {
    hasBlockscoutKey: false,
    hasEtherscanKey: false,
    hasGnosisEvents: true,
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
  it('should not ask users without gnosis events', () => {
    expect(createGnosisIndexerSuggestion(t, createContext({ hasGnosisEvents: false }))).toBeUndefined();
  });

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
