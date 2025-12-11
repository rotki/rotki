import type { ExchangeData } from '@/types/exchanges';
import { type AssetBalanceWithPrice, bigNumberify, Blockchain, Zero } from '@rotki/common';
import {
  createProtocolTestBalance,
  createTestBalance,
  createTestManualBalance,
  createTestPriceInfo,
} from '@test/utils/create-data';
import { updateGeneralSettings } from '@test/utils/general-settings';
import {
  createMockExchangeBalances,
  testAccounts,
  testEthereumBalances,
  testExchangeBalances,
  testManualBalances,
} from '@test/utils/test-data';
import { sortBy } from 'es-toolkit';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TRADE_LOCATION_BANKS } from '@/data/defaults';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useSessionSettingsStore } from '@/store/settings/session';
import { BalanceType } from '@/types/balances';
import { useAggregatedBalances } from './use-aggregated-balances';
import '@test/i18n';

vi.mock('@/modules/assets/use-collection-info', () => ({
  useCollectionInfo: (): any => ({
    useCollectionId: vi.fn((asset: string) => computed(() => {
      if (asset === 'ETH' || asset === 'WETH') {
        return '21';
      }
      else if (asset.endsWith('USDC')) {
        return 'USDC';
      }
      return undefined;
    })),
    useCollectionMainAsset: vi.fn((collectionId: string) => computed(() => {
      if (collectionId === '21') {
        return 'ETH';
      }
      else if (collectionId.endsWith('USDC')) {
        return 'USDC';
      }
      return undefined;
    })),
  }),
}));

describe('useAggregatedBalances', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('should aggregate balances from multiple sources with manual balance tracking', () => {
    const { balances: ethBalances, exchangeBalances, manualBalances } = storeToRefs(useBalancesStore());
    const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
    const { prices } = storeToRefs(useBalancePricesStore());
    const { balances } = useAggregatedBalances();

    set(connectedExchanges, [{
      location: 'kraken',
      name: 'Bitrex Acc',
    }]);

    set(exchangeBalances, {
      kraken: {
        BTC: createTestBalance(50, 50),
        DAI: createTestBalance(50, 50),
        ETH: createTestBalance(50, 50),
        EUR: createTestBalance(50, 50),
      },
    });

    set(prices, {
      BTC: createTestPriceInfo(40000),
      DAI: createTestPriceInfo(1),
      ETH: createTestPriceInfo(3000),
      EUR: createTestPriceInfo(1),
      SAI: createTestPriceInfo(1),
    });

    set(manualBalances, [
      createTestManualBalance('DAI', 50, 50, TRADE_LOCATION_BANKS),
      createTestManualBalance('DAI', 10, 10, 'aave', BalanceType.ASSET, 2),
    ]);

    set(ethBalances, {
      [Blockchain.ETH.toString()]: {
        '0x123': {
          assets: {
            BTC: { address: createTestBalance(100, 100) },
            DAI: {
              aave: createTestBalance(10, 10),
              address: createTestBalance(100, 100),
            },
            ETH: { address: createTestBalance(100, 100) },
            SAI: { address: createTestBalance(100, 100) },
          },
          liabilities: {},
        },
      },
    });

    const actualResult = sortBy(get(balances()), ['asset']);

    const expectedResult = sortBy([{
      amount: bigNumberify(50),
      asset: 'EUR',
      perProtocol: [
        createProtocolTestBalance('kraken', 50, 50),
      ],
      usdPrice: bigNumberify(1),
      value: bigNumberify(50),
    }, {
      amount: bigNumberify(220),
      asset: 'DAI',
      perProtocol: [
        createProtocolTestBalance('address', 100, 100),
        createProtocolTestBalance('banks', 50, 50),
        createProtocolTestBalance('kraken', 50, 50),
        createProtocolTestBalance('aave', 20, 20, true),
      ],
      usdPrice: bigNumberify(1),
      value: bigNumberify(220),
    }, {
      amount: bigNumberify(150),
      asset: 'BTC',
      perProtocol: [
        createProtocolTestBalance('address', 100, 100),
        createProtocolTestBalance('kraken', 50, 50),
      ],
      usdPrice: bigNumberify(40000),
      value: bigNumberify(150),
    }, {
      amount: bigNumberify(150),
      asset: 'ETH',
      perProtocol: [
        createProtocolTestBalance('address', 100, 100),
        createProtocolTestBalance('kraken', 50, 50),
      ],
      usdPrice: bigNumberify(3000),
      value: bigNumberify(150),
    }, {
      amount: bigNumberify(100),
      asset: 'SAI',
      perProtocol: [
        createProtocolTestBalance('address', 100, 100),
      ],
      usdPrice: bigNumberify(1),
      value: bigNumberify(100),
    }] satisfies AssetBalanceWithPrice[], ['asset']);

    expect(actualResult).toMatchObject(expectedResult);
  });

  describe('balances', () => {
    it('should return empty array when no balances exist', () => {
      const { balances } = useAggregatedBalances();
      const result = get(balances());
      expect(result).toEqual([]);
    });

    it('should respect hideIgnored parameter', () => {
      const { exchangeBalances } = storeToRefs(useBalancesStore());
      const { balances } = useAggregatedBalances();

      set(exchangeBalances, {
        kraken: {
          BTC: createTestBalance(1, 50000),
        },
      });

      const ignoredStore = useIgnoredAssetsStore();
      ignoredStore.ignoredAssets.push('BTC');
      const hidden = get(balances(true));
      const visible = get(balances(false));

      expect(hidden).toHaveLength(0);
      expect(visible).toHaveLength(1);
    });

    it('should support groupCollections parameter', () => {
      const { balances } = useAggregatedBalances();

      const grouped = get(balances(true, true));
      const ungrouped = get(balances(true, false));

      expect(Array.isArray(grouped)).toBe(true);
      expect(Array.isArray(ungrouped)).toBe(true);
    });

    it('should support exclusion sources parameter', () => {
      const { balances } = useAggregatedBalances();

      const allSources = get(balances(true, true, []));
      const excludeManual = get(balances(true, true, ['manual']));
      const excludeExchange = get(balances(true, true, ['exchange']));

      expect(Array.isArray(allSources)).toBe(true);
      expect(Array.isArray(excludeManual)).toBe(true);
      expect(Array.isArray(excludeExchange)).toBe(true);
    });
  });

  describe('liabilities', () => {
    it('should return empty array when no liabilities exist', () => {
      const { liabilities } = useAggregatedBalances();
      const result = get(liabilities());
      expect(result).toEqual([]);
    });

    it('should respect hideIgnored parameter for liabilities', () => {
      const { liabilities } = useAggregatedBalances();

      const hidden = get(liabilities(true));
      const visible = get(liabilities(false));

      expect(Array.isArray(hidden)).toBe(true);
      expect(Array.isArray(visible)).toBe(true);
    });

    it('should aggregate liabilities from blockchain and manual sources', () => {
      const { manualLiabilities } = storeToRefs(useBalancesStore());
      const { liabilities } = useAggregatedBalances();

      set(manualLiabilities, [
        createTestManualBalance('DAI', 100, 100, 'compound', BalanceType.LIABILITY),
      ]);

      const result = get(liabilities());
      expect(result).toEqual([{
        amount: bigNumberify(100),
        asset: 'DAI',
        perProtocol: [
          createProtocolTestBalance('compound', 100, 100, true),
        ],
        usdPrice: bigNumberify(-1),
        value: bigNumberify(100),
      }]);
    });
  });

  describe('assets', () => {
    it('should return empty array when no assets exist', () => {
      const { assets } = useAggregatedBalances();
      const result = get(assets);
      expect(result).toEqual([]);
    });

    it('should include assets from all balance sources', () => {
      const { balances: blockchainBalances, exchangeBalances, manualBalances } = storeToRefs(useBalancesStore());
      const { assets } = useAggregatedBalances();

      set(manualBalances, [
        createTestManualBalance('DAI', 100, 100, 'banks'),
      ]);

      set(exchangeBalances, {
        kraken: {
          BTC: createTestBalance(1, 50000),
        },
      });

      set(blockchainBalances, {
        [Blockchain.ETH]: {
          '0x123': {
            assets: {
              ETH: {
                address: createTestBalance(10, 30000),
              },
            },
            liabilities: {},
          },
        },
      });

      const result = get(assets);
      expect(result).toContain('DAI');
      expect(result).toContain('BTC');
      expect(result).toContain('ETH');
    });
  });

  describe('assetPriceInfo', () => {
    it('should return zero values for non-existent asset', () => {
      const { assetPriceInfo } = useAggregatedBalances();
      const result = get(assetPriceInfo('NON_EXISTENT'));

      expect(result).toMatchObject({
        amount: Zero,
        usdPrice: Zero,
        value: Zero,
      });
    });

    it('should return correct price info for existing asset', () => {
      const { exchangeBalances } = storeToRefs(useBalancesStore());
      const { prices } = storeToRefs(useBalancePricesStore());
      const { assetPriceInfo } = useAggregatedBalances();

      set(exchangeBalances, {
        kraken: {
          BTC: createTestBalance(1, 50000),
        },
      });

      set(prices, {
        BTC: createTestPriceInfo(50000),
      });

      const result = get(assetPriceInfo('BTC'));

      expect(result.amount).toEqual(bigNumberify(1));
      expect(result.usdPrice).toEqual(bigNumberify(50000));
      expect(result.value).toEqual(bigNumberify(50000));
    });

    it('should support groupMultiChain parameter', () => {
      const { balances: blockchainBalances, exchangeBalances } = storeToRefs(useBalancesStore());
      const { prices } = storeToRefs(useBalancePricesStore());
      const { assetPriceInfo } = useAggregatedBalances();

      set(blockchainBalances, {
        [Blockchain.ETH]: {
          '0x123': {
            assets: {
              ETH: {
                address: createTestBalance(1, 40000),
              },
              WETH: {
                address: createTestBalance(0.5, 20000),
              },
            },
            liabilities: {},
          },
        },
      });

      set(exchangeBalances, {
        kraken: {
          ETH: createTestBalance(2, 80000),
        },
      });

      set(prices, {
        ETH: createTestPriceInfo(40000),
        WETH: createTestPriceInfo(40000),
      });

      const ungrouped = get(assetPriceInfo('ETH', false));
      const grouped = get(assetPriceInfo('ETH', true));

      // Ungrouped should only show ETH balances (no collection grouping)
      expect(ungrouped.amount).toEqual(bigNumberify(3));
      expect(ungrouped.usdPrice).toEqual(bigNumberify(40000));
      expect(ungrouped.value).toEqual(bigNumberify(120000));

      // Grouped should include both ETH and WETH in the collection
      expect(grouped.amount).toEqual(bigNumberify(3.5));
      expect(grouped.usdPrice).toEqual(bigNumberify(40000));
      expect(grouped.value).toEqual(bigNumberify(140000));
    });

    it('should work with reactive identifier', () => {
      const { assetPriceInfo } = useAggregatedBalances();
      const reactiveAsset = ref('BTC');

      const result = get(assetPriceInfo(reactiveAsset));

      expect(result).toHaveProperty('amount');
      expect(result).toHaveProperty('usdPrice');
      expect(result).toHaveProperty('value');

      reactiveAsset.value = 'ETH';

      const updatedResult = get(assetPriceInfo(reactiveAsset));
      expect(updatedResult).toHaveProperty('amount');
    });
  });

  describe('collection grouping with missing main asset', () => {
    it('should create main asset with zero balance when user owns collection asset but not main asset', () => {
      const { balances: blockchainBalances } = storeToRefs(useBalancesStore());
      const { prices } = storeToRefs(useBalancePricesStore());
      const { balances } = useAggregatedBalances();

      // User has WETH but not ETH (the main asset of the ethereum collection)
      set(blockchainBalances, {
        [Blockchain.ETH]: {
          '0x123': {
            assets: {
              WETH: {
                uniswap: createTestBalance(10, 40000),
              },
            },
            liabilities: {},
          },
        },
      });

      set(prices, {
        ETH: createTestPriceInfo(4000),
        WETH: createTestPriceInfo(4000),
      });

      const result = get(balances(true, true));

      // Should return one result (the ethereum collection)
      expect(result).toHaveLength(1);

      const collectionResult = result[0];

      // Should use ETH as the main asset (not WETH)
      expect(collectionResult.asset).toBe('ETH');
      expect(collectionResult.usdPrice).toEqual(bigNumberify(4000));

      // Should have breakdown only WETH
      expect(collectionResult.breakdown).toHaveLength(1);

      // Find ETH and WETH in breakdown
      const ethBreakdown = collectionResult.breakdown?.find(item => item.asset === 'ETH');
      const wethBreakdown = collectionResult.breakdown?.find(item => item.asset === 'WETH');

      // ETH should not be present
      expect(ethBreakdown).toBeUndefined();

      // WETH should have the original balance
      expect(wethBreakdown).toBeDefined();
      expect(wethBreakdown?.amount).toEqual(bigNumberify(10));
      expect(wethBreakdown?.value).toEqual(bigNumberify(40000));
      expect(wethBreakdown?.perProtocol).toHaveLength(1);
      expect(wethBreakdown?.perProtocol?.[0].protocol).toBe('uniswap');
    });

    it('should not duplicate main asset when it already exists in collection', () => {
      const { balances: blockchainBalances } = storeToRefs(useBalancesStore());
      const { prices } = storeToRefs(useBalancePricesStore());
      const { balances } = useAggregatedBalances();

      // User has both ETH and WETH
      set(blockchainBalances, {
        [Blockchain.ETH]: {
          '0x123': {
            assets: {
              ETH: {
                address: createTestBalance(5, 20000),
              },
              WETH: {
                uniswap: createTestBalance(10, 40000),
              },
            },
            liabilities: {},
          },
        },
      });

      set(prices, {
        ETH: createTestPriceInfo(4000),
        WETH: createTestPriceInfo(4000),
      });

      const result = get(balances(true, true));

      expect(result).toHaveLength(1);
      const collectionResult = result[0];

      // Should still use ETH as main asset
      expect(collectionResult.asset).toBe('ETH');
      expect(collectionResult.amount).toEqual(bigNumberify(15));
      expect(collectionResult.value).toEqual(bigNumberify(60000));

      // Should have breakdown with both assets, no duplicate ETH created
      expect(collectionResult.breakdown).toHaveLength(2);

      const ethItems = collectionResult.breakdown?.filter(item => item.asset === 'ETH') || [];
      expect(ethItems).toHaveLength(1); // Only one ETH entry

      // ETH should have its original balance
      const ethBreakdown = ethItems[0];
      expect(ethBreakdown.amount).toEqual(bigNumberify(5));
      expect(ethBreakdown.value).toEqual(bigNumberify(20000));
    });
  });

  describe('useLocationBreakdown', () => {
    it('should return location breakdown for manual balances with asset association support', async () => {
      const { manualBalances } = storeToRefs(useBalancesStore());
      const { useLocationBreakdown } = useAggregatedBalances();

      // Set up manual balances with ETH and ETH2
      const ethAndEth2Balances = [{
        amount: bigNumberify(50),
        asset: 'ETH',
        balanceType: BalanceType.ASSET,
        identifier: 4,
        label: 'Ethereum',
        location: 'external',
        tags: [],
        value: bigNumberify(50),
      }, {
        amount: bigNumberify(100),
        asset: 'ETH2',
        balanceType: BalanceType.ASSET,
        identifier: 5,
        label: 'Staked ETH',
        location: 'external',
        tags: [],
        value: bigNumberify(100),
      }];

      set(manualBalances, ethAndEth2Balances);

      updateGeneralSettings({ treatEth2AsEth: false });

      const breakdown = useLocationBreakdown('external');

      expect(get(breakdown)).toMatchObject([{
        amount: bigNumberify(50),
        asset: 'ETH',
        perProtocol: [{
          amount: bigNumberify(50),
          containsManual: true,
          protocol: 'external',
          value: bigNumberify(50),
        }],
        usdPrice: bigNumberify(-1),
        value: bigNumberify(50),
      }, {
        amount: bigNumberify(100),
        asset: 'ETH2',
        perProtocol: [{
          amount: bigNumberify(100),
          containsManual: true,
          protocol: 'external',
          value: bigNumberify(100),
        }],
        usdPrice: bigNumberify(-1),
        value: bigNumberify(100),
      }]);

      updateGeneralSettings({ treatEth2AsEth: true });

      expect(get(breakdown)).toMatchObject([{
        amount: bigNumberify(150),
        asset: 'ETH',
        usdPrice: bigNumberify(-1),
        value: bigNumberify(150),
      }]);
    });

    it('should return location breakdown with collection grouping for complex assets', () => {
      const { exchangeBalances, manualBalances } = storeToRefs(useBalancesStore());
      const { updateBalances } = useBalancesStore();
      const { updateAccounts } = useBlockchainAccountsStore();
      const { connectedExchanges } = storeToRefs(useSessionSettingsStore());

      // Set up test data for collection grouping
      set(connectedExchanges, [{
        location: 'kraken',
        name: 'Kraken 1',
      }]);

      set(manualBalances, testManualBalances);
      set(exchangeBalances, testExchangeBalances);
      updateBalances('eth', testEthereumBalances);
      updateAccounts('eth', testAccounts);

      const { fetchedAssetCollections } = storeToRefs(useAssetCacheStore());
      const { useLocationBreakdown } = useAggregatedBalances();
      set(fetchedAssetCollections, {
        GNO: {
          mainAsset: 'GNO',
          name: 'GNO',
          symbol: 'GNO',
        },
        USDC: {
          mainAsset: 'USDC',
          name: 'USDC',
          symbol: 'USDC',
        },
      });
      const locationBreakdown = useLocationBreakdown('kraken');
      const expectedResult: AssetBalanceWithPrice[] = [{
        amount: bigNumberify(4000),
        asset: 'USDC',
        breakdown: [{
          amount: bigNumberify(2500),
          asset: 'aUSDC',
          perProtocol: [{
            amount: bigNumberify(2500),
            containsManual: true,
            protocol: 'kraken',
            value: bigNumberify(2500),
          }],
          usdPrice: bigNumberify(-1),
          value: bigNumberify(2500),
        }, {
          amount: bigNumberify(1000),
          asset: 'cUSDC',
          perProtocol: [{
            amount: bigNumberify(1000),
            protocol: 'kraken',
            value: bigNumberify(1000),
          }],
          usdPrice: bigNumberify(-1),
          value: bigNumberify(1000),
        }, {
          amount: bigNumberify(500),
          asset: 'bUSDC',
          perProtocol: [{
            amount: bigNumberify(500),
            containsManual: true,
            protocol: 'kraken',
            value: bigNumberify(500),
          }],
          usdPrice: bigNumberify(-1),
          value: bigNumberify(500),
        }],
        perProtocol: [{
          amount: bigNumberify(4000),
          containsManual: true,
          protocol: 'kraken',
          value: bigNumberify(4000),
        }],
        usdPrice: bigNumberify(-1),
        value: bigNumberify(4000),
      }, {
        amount: bigNumberify(2000),
        asset: 'GNO',
        perProtocol: [{
          amount: bigNumberify(2000),
          containsManual: true,
          protocol: 'kraken',
          value: bigNumberify(2000),
        }],
        usdPrice: bigNumberify(-1),
        value: bigNumberify(2000),
      }];
      expect(get(locationBreakdown)).toStrictEqual(expectedResult);
    });

    it('should handle asset association for location breakdown in exchange balances', async () => {
      const { exchangeBalances } = storeToRefs(useBalancesStore());
      const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
      const { useLocationBreakdown } = useAggregatedBalances();

      const mockBalances: ExchangeData = {
        kraken: {
          ETH: createTestBalance(1000, 1000),
          ETH2: createTestBalance(1000, 1000),
        },
      };

      set(exchangeBalances, mockBalances);
      set(connectedExchanges, [{
        location: 'kraken',
        name: 'Kraken',
      }]);

      updateGeneralSettings({ treatEth2AsEth: false });

      const locationBreakdown = useLocationBreakdown('kraken');

      expect(get(locationBreakdown)).toMatchObject([{
        amount: bigNumberify(1000),
        asset: 'ETH',
        perProtocol: [
          createProtocolTestBalance('kraken', 1000, 1000),
        ],
        usdPrice: bigNumberify(-1),
        value: bigNumberify(1000),
      }, {
        amount: bigNumberify(1000),
        asset: 'ETH2',
        perProtocol: [
          createProtocolTestBalance('kraken', 1000, 1000),
        ],
        usdPrice: bigNumberify(-1),
        value: bigNumberify(1000),
      }]);

      updateGeneralSettings({ treatEth2AsEth: true });

      await nextTick();

      expect(get(locationBreakdown)).toMatchObject([{
        amount: bigNumberify(2000),
        asset: 'ETH',
        perProtocol: [
          createProtocolTestBalance('kraken', 2000, 2000),
        ],
        usdPrice: bigNumberify(-1),
        value: bigNumberify(2000),
      }]);
    });

    it('should respect the asset association for the location breakdown', async () => {
      const sessionSettingsStore = useSessionSettingsStore();
      const { useLocationBreakdown } = useAggregatedBalances();
      const { connectedExchanges } = storeToRefs(sessionSettingsStore);
      const { exchangeBalances } = storeToRefs(useBalancesStore());
      set(exchangeBalances, createMockExchangeBalances());

      set(connectedExchanges, [{
        location: 'kraken',
        name: 'Kraken',
      }, {
        location: 'coinbase',
        name: 'Coinbase',
      }]);

      updateGeneralSettings({ treatEth2AsEth: false });

      const locationBreakdown = useLocationBreakdown('kraken');

      expect(get(locationBreakdown)).toMatchObject([{
        amount: bigNumberify(1000),
        asset: 'ETH',
        perProtocol: [
          createProtocolTestBalance('kraken', 1000, 1000),
        ],
        usdPrice: bigNumberify(-1),
        value: bigNumberify(1000),
      }, {
        amount: bigNumberify(1000),
        asset: 'ETH2',
        perProtocol: [
          createProtocolTestBalance('kraken', 1000, 1000),
        ],
        usdPrice: bigNumberify(-1),
        value: bigNumberify(1000),
      }]);

      updateGeneralSettings({ treatEth2AsEth: true });

      await nextTick();

      expect(get(locationBreakdown)).toMatchObject([{
        amount: bigNumberify(2000),
        asset: 'ETH',
        perProtocol: [
          createProtocolTestBalance('kraken', 2000, 2000),
        ],
        usdPrice: bigNumberify(-1),
        value: bigNumberify(2000),
      }]);
    });
  });
});
