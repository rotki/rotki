import { describe, expect, it, vi } from 'vitest';
import {
  buildTabs,
  DEFAULT_INDEXER_TAB,
  getAvailableChainItems,
  getAvailableIndexersForChain,
  getChainIndexerWarnings,
  getMissingApiKeyIndexer,
  isEvmIndexer,
  keyedPrimaryIndexer,
  orderForChain,
  toChainIdKeys,
  toEvmChainNameKeys,
} from '@/modules/settings/evm/evm-indexer-utils';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';
import { EmptyListId } from '@/modules/settings/types/prioritized-list-id';

describe('evm-indexer-utils', () => {
  describe('isEvmIndexer', () => {
    it('should accept every indexer id', () => {
      expect(isEvmIndexer(EvmIndexer.ETHERSCAN)).toBe(true);
      expect(isEvmIndexer(EvmIndexer.BLOCKSCOUT)).toBe(true);
      expect(isEvmIndexer(EvmIndexer.ROUTESCAN)).toBe(true);
    });

    it('should reject an id from another prioritized list', () => {
      expect(isEvmIndexer(EmptyListId)).toBe(false);
    });
  });

  describe('getAvailableIndexersForChain', () => {
    it('should offer every indexer for the default tab', () => {
      const available = getAvailableIndexersForChain(null);

      expect(available.itemDataForId(EvmIndexer.ETHERSCAN)).toBeDefined();
      expect(available.itemDataForId(EvmIndexer.BLOCKSCOUT)).toBeDefined();
      expect(available.itemDataForId(EvmIndexer.ROUTESCAN)).toBeDefined();
    });

    it('should offer every indexer for a chain with no restriction', () => {
      const available = getAvailableIndexersForChain('optimism');

      expect(available.itemDataForId(EvmIndexer.BLOCKSCOUT)).toBeDefined();
    });

    it('should restrict a chain that only one indexer serves', () => {
      const available = getAvailableIndexersForChain('binance_sc');

      expect(available.itemDataForId(EvmIndexer.ETHERSCAN)).toBeDefined();
      expect(available.itemDataForId(EvmIndexer.BLOCKSCOUT)).toBeUndefined();
      expect(available.itemDataForId(EvmIndexer.ROUTESCAN)).toBeUndefined();
    });
  });

  describe('orderForChain', () => {
    it('should keep the order a chain fully supports', () => {
      expect(orderForChain('optimism', [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN]))
        .toEqual([EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN]);
    });

    it('should drop the indexers a restricted chain cannot use', () => {
      expect(orderForChain('binance_sc', [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN]))
        .toEqual([EvmIndexer.ETHERSCAN]);
    });

    it('should fall back to etherscan rather than leave a chain with no indexer', () => {
      expect(orderForChain('binance_sc', [EvmIndexer.BLOCKSCOUT, EvmIndexer.ROUTESCAN]))
        .toEqual([EvmIndexer.ETHERSCAN]);
      expect(orderForChain('optimism', [])).toEqual([EvmIndexer.ETHERSCAN]);
    });
  });

  describe('toEvmChainNameKeys', () => {
    const getEvmChainName = (chain: string): string | undefined =>
      chain === 'unknown' ? undefined : `${chain}_name`;

    it('should rekey the orders by evm chain name', () => {
      expect(toEvmChainNameKeys({ optimism: [EvmIndexer.ETHERSCAN] }, getEvmChainName))
        .toEqual({ optimism_name: [EvmIndexer.ETHERSCAN] });
    });

    it('should drop a chain with no evm chain name', () => {
      expect(toEvmChainNameKeys({ unknown: [EvmIndexer.ETHERSCAN] }, getEvmChainName)).toEqual({});
    });

    it('should drop entries that are not indexers', () => {
      expect(toEvmChainNameKeys({ optimism: [EmptyListId, EvmIndexer.ETHERSCAN] }, getEvmChainName))
        .toEqual({ optimism_name: [EvmIndexer.ETHERSCAN] });
    });
  });

  describe('toChainIdKeys', () => {
    const getChain = (evmChainName: string): string => evmChainName.replace('_name', '');

    it('should rekey the stored orders by chain id', () => {
      expect(toChainIdKeys({ optimism_name: [EvmIndexer.ETHERSCAN] }, getChain))
        .toEqual({ optimism: [EvmIndexer.ETHERSCAN] });
    });

    it('should return an empty record when nothing is stored', () => {
      expect(toChainIdKeys(undefined, getChain)).toEqual({});
    });

    it('should copy the stored arrays rather than alias them', () => {
      const stored = { optimism_name: [EvmIndexer.ETHERSCAN] };
      const converted = toChainIdKeys(stored, getChain);
      converted.optimism.push(EvmIndexer.BLOCKSCOUT);

      expect(stored.optimism_name).toEqual([EvmIndexer.ETHERSCAN]);
    });
  });

  describe('buildTabs', () => {
    it('should always lead with the default tab', () => {
      expect(buildTabs([], () => 'unused')).toEqual([{ id: DEFAULT_INDEXER_TAB, isDefault: true }]);
    });

    it('should name each configured chain', () => {
      const getChainName = vi.fn<(chain: string) => string>().mockReturnValue('Optimism');

      expect(buildTabs(['optimism'], getChainName)).toEqual([
        { id: DEFAULT_INDEXER_TAB, isDefault: true },
        { id: 'optimism', isDefault: false, name: 'Optimism' },
      ]);
    });
  });

  describe('getAvailableChainItems', () => {
    it('should exclude the chains that already have an override', () => {
      const chains = [{ id: 'optimism', name: 'Optimism' }, { id: 'base', name: 'Base' }];

      expect(getAvailableChainItems(chains, ['optimism'])).toEqual([{ id: 'base', name: 'Base' }]);
    });
  });

  describe('getChainIndexerWarnings', () => {
    it('should not warn on the default tab', () => {
      expect(getChainIndexerWarnings(DEFAULT_INDEXER_TAB, [EvmIndexer.BLOCKSCOUT])).toEqual([]);
    });

    it('should warn when optimism includes blockscout', () => {
      expect(getChainIndexerWarnings('optimism', [EvmIndexer.BLOCKSCOUT]))
        .toEqual(['evm_settings.indexer.chain_warnings.optimism_blockscout']);
      expect(getChainIndexerWarnings('optimism', [EvmIndexer.ETHERSCAN])).toEqual([]);
    });

    it('should warn when base does not lead with blockscout', () => {
      expect(getChainIndexerWarnings('base', [EvmIndexer.ETHERSCAN]))
        .toEqual(['evm_settings.indexer.chain_warnings.base_limited_indexers']);
      expect(getChainIndexerWarnings('base', []))
        .toEqual(['evm_settings.indexer.chain_warnings.base_limited_indexers']);
      expect(getChainIndexerWarnings('base', [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN])).toEqual([]);
    });

    it('should always warn on gnosis', () => {
      expect(getChainIndexerWarnings('gnosis', [EvmIndexer.ETHERSCAN]))
        .toEqual(['evm_settings.indexer.chain_warnings.gnosis_key_required']);
    });

    it('should return an empty list for a chain with no caveat', () => {
      expect(getChainIndexerWarnings('arbitrum_one', [EvmIndexer.BLOCKSCOUT])).toEqual([]);
    });
  });

  describe('keyedPrimaryIndexer', () => {
    it('should name the leading indexer when it needs a key', () => {
      expect(keyedPrimaryIndexer([EvmIndexer.ETHERSCAN, EvmIndexer.ROUTESCAN])).toBe(EvmIndexer.ETHERSCAN);
      expect(keyedPrimaryIndexer([EvmIndexer.BLOCKSCOUT])).toBe(EvmIndexer.BLOCKSCOUT);
    });

    it('should ignore an indexer that needs no key', () => {
      expect(keyedPrimaryIndexer([EvmIndexer.ROUTESCAN, EvmIndexer.ETHERSCAN])).toBeUndefined();
    });

    it('should ignore an empty order', () => {
      expect(keyedPrimaryIndexer([])).toBeUndefined();
    });
  });

  describe('getMissingApiKeyIndexer', () => {
    const noKeys = (): boolean => false;
    const allKeys = (): boolean => true;

    it('should name the leading indexer whose key is missing', () => {
      expect(getMissingApiKeyIndexer([EvmIndexer.ETHERSCAN], noKeys)).toBe('Etherscan');
      expect(getMissingApiKeyIndexer([EvmIndexer.BLOCKSCOUT], noKeys)).toBe('Blockscout');
    });

    it('should stay quiet once the key is entered', () => {
      expect(getMissingApiKeyIndexer([EvmIndexer.ETHERSCAN], allKeys)).toBeUndefined();
    });

    it('should only consider the leading indexer', () => {
      expect(getMissingApiKeyIndexer([EvmIndexer.ROUTESCAN, EvmIndexer.ETHERSCAN], noKeys)).toBeUndefined();
    });

    it('should ask about the leading indexer only', () => {
      const hasApiKey = vi.fn<(indexer: EvmIndexer) => boolean>().mockReturnValue(true);
      getMissingApiKeyIndexer([EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN], hasApiKey);

      expect(hasApiKey).toHaveBeenCalledExactlyOnceWith(EvmIndexer.BLOCKSCOUT);
    });
  });
});
