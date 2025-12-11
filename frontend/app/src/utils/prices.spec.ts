import type { ProtocolBalances } from '@/types/blockchain/balances';
import { bigNumberify } from '@rotki/common';
import {
  createTestBalance,
  createTestPriceInfo,
} from '@test/utils/create-data';
import { describe, expect, it } from 'vitest';
import { updateBalancesPrices, updateBlockchainAssetBalances, updateExchangeBalancesPrices } from '@/utils/prices';

describe('utils/prices', () => {
  const mockPrices = {
    BTC: createTestPriceInfo(40000, 'cryptocompare'),
    DAI: createTestPriceInfo(1, 'coingecko'),
    ETH: createTestPriceInfo(2000, 'coingecko', false, 2500),
  };

  describe('updateBalancesPrices', () => {
    it('should update balances with USD prices', () => {
      const balances = {
        BTC: {
          protocol1: createTestBalance(2, 80000),
        },
        ETH: {
          compound: createTestBalance(5, 10000),
          uniswap: createTestBalance(10, 20000),
        },
      };

      const result = updateBalancesPrices(balances, mockPrices);

      // Uses price.value (2000) for ETH, not usdPrice (2500)
      expect(result.ETH.uniswap.value).toEqual(bigNumberify(20000));
      expect(result.ETH.compound.value).toEqual(bigNumberify(10000));
      expect(result.BTC.protocol1.value).toEqual(bigNumberify(80000));
    });

    it('should handle empty balances', () => {
      const result = updateBalancesPrices({}, mockPrices);
      expect(result).toEqual({});
    });

    it('should preserve balances for assets without prices', () => {
      const balances = {
        UNKNOWN: {
          protocol1: createTestBalance(100, 0),
        },
      };

      const result = updateBalancesPrices(balances, mockPrices);
      expect(result.UNKNOWN).toEqual(balances.UNKNOWN);
    });

    it('should use value as fallback when usdPrice is not available', () => {
      const balances = {
        BTC: {
          protocol1: createTestBalance(1, 0),
        },
      };

      const result = updateBalancesPrices(balances, mockPrices);
      expect(result.BTC.protocol1.value).toEqual(bigNumberify(40000));
    });

    it('should handle empty protocols', () => {
      const balances = { ETH: {} };

      const result = updateBalancesPrices(balances, mockPrices);
      expect(result.ETH).toEqual({});
    });

    it('should work with createTestBalance helper', () => {
      const balances = {
        ETH: {
          protocol1: createTestBalance(1, 2000),
          protocol2: createTestBalance(2, 4000),
        },
      };

      const result = updateBalancesPrices(balances, mockPrices);

      // Uses price.value (2000) for ETH, not usdPrice (2500)
      expect(result.ETH.protocol1.value).toEqual(bigNumberify(2000));
      expect(result.ETH.protocol2.value).toEqual(bigNumberify(4000));
    });
  });

  describe('updateExchangeBalancesPrices', () => {
    it('should update exchange balances with USD prices', () => {
      const balances = {
        DAI: createTestBalance(1000, 1000),
        ETH: createTestBalance(10, 20000),
      };

      const result = updateExchangeBalancesPrices(balances, mockPrices);

      // Uses price.value (2000) for ETH, not usdPrice (2500)
      expect(result.ETH.value).toEqual(bigNumberify(20000));
      expect(result.DAI.value).toEqual(bigNumberify(1000));
    });

    it('should handle empty balances', () => {
      const result = updateExchangeBalancesPrices({}, mockPrices);
      expect(result).toEqual({});
    });

    it('should preserve balances for assets without prices', () => {
      const balances = {
        UNKNOWN: createTestBalance(100, 500),
      };

      const result = updateExchangeBalancesPrices(balances, mockPrices);
      expect(result.UNKNOWN).toEqual(balances.UNKNOWN);
    });
  });

  describe('updateBlockchainAssetBalances', () => {
    it('should update blockchain balances with prices for multiple chains and addresses', () => {
      const balances = {
        btc: {
          bc1Address: {
            assets: { BTC: { native: createTestBalance(2, 80000) } },
            liabilities: {},
          },
        },
        eth: {
          '0xAddress1': {
            assets: { ETH: { native: createTestBalance(10, 20000) } },
            liabilities: { DAI: { compound: createTestBalance(1000, 1000) } },
          },
          '0xAddress2': {
            assets: { ETH: { uniswap: createTestBalance(5, 10000) } },
            liabilities: {},
          },
        },
      };

      const result = updateBlockchainAssetBalances(balances, mockPrices);

      // Uses price.value (2000) for ETH, not usdPrice (2500)
      expect(result.eth['0xAddress1'].assets.ETH.native.value).toEqual(bigNumberify(20000));
      expect(result.eth['0xAddress1'].liabilities.DAI.compound.value).toEqual(bigNumberify(1000));
      expect(result.eth['0xAddress2'].assets.ETH.uniswap.value).toEqual(bigNumberify(10000));
      expect(result.btc.bc1Address.assets.BTC.native.value).toEqual(bigNumberify(80000));
    });

    it('should handle empty balances', () => {
      const result = updateBlockchainAssetBalances({}, mockPrices);
      expect(result).toEqual({});
    });

    it('should handle chains with no addresses', () => {
      const balances = { eth: {} };

      const result = updateBlockchainAssetBalances(balances, mockPrices);
      expect(result).toEqual({ eth: {} });
    });

    it('should preserve immutability', () => {
      const balances = {
        eth: {
          '0xAddress': {
            assets: { ETH: { native: createTestBalance(10, 20000) } },
            liabilities: {},
          },
        },
      };

      const result = updateBlockchainAssetBalances(balances, mockPrices);

      expect(result).not.toBe(balances);
      expect(result.eth).not.toBe(balances.eth);
      expect(result.eth['0xAddress']).not.toBe(balances.eth['0xAddress']);
      expect(result.eth['0xAddress'].assets).not.toBe(balances.eth['0xAddress'].assets);
    });

    it('should handle missing prices for some assets', () => {
      const balances = {
        eth: {
          '0xAddress': {
            assets: {
              ETH: { native: createTestBalance(10, 20000) },
              UNKNOWN: { protocol: createTestBalance(100, 0) },
            },
            liabilities: {},
          },
        },
      };

      const result = updateBlockchainAssetBalances(balances, mockPrices);

      // Uses price.value (2000) for ETH, not usdPrice (2500)
      expect(result.eth['0xAddress'].assets.ETH.native.value).toEqual(bigNumberify(20000));
      expect(result.eth['0xAddress'].assets.UNKNOWN).toEqual(balances.eth['0xAddress'].assets.UNKNOWN);
    });

    it('should handle complex nested structures efficiently', () => {
      const balances = {
        eth: {
          '0xAddress1': {
            assets: {
              DAI: { protocol2: createTestBalance(100, 0) },
              ETH: { protocol1: createTestBalance(1, 0) },
            },
            liabilities: { DAI: { lending1: createTestBalance(50, 0) } },
          },
        },
        polygon: {
          '0xAddress2': {
            assets: { ETH: { bridge: createTestBalance(2, 0) } },
            liabilities: {},
          },
        },
      };

      const result = updateBlockchainAssetBalances(balances, mockPrices);

      // Uses price.value (2000) for ETH, not usdPrice (2500)
      expect(result.eth['0xAddress1'].assets.ETH.protocol1.value).toEqual(bigNumberify(2000));
      expect(result.eth['0xAddress1'].assets.DAI.protocol2.value).toEqual(bigNumberify(100));
      expect(result.eth['0xAddress1'].liabilities.DAI.lending1.value).toEqual(bigNumberify(50));
      expect(result.polygon['0xAddress2'].assets.ETH.bridge.value).toEqual(bigNumberify(4000));
    });
  });

  describe('performance characteristics', () => {
    it('should handle large datasets efficiently', () => {
      // Create test data using utilities
      const assetsData: Record<string, ProtocolBalances> = {};
      const pricesData: Record<string, { value: number; oracle?: string }> = {};

      // Create 1000 assets with 5 protocols each
      for (let i = 0; i < 1000; i++) {
        const asset = `ASSET_${i}`;
        assetsData[asset] = {};
        pricesData[asset] = { oracle: 'test', value: 100 + i };

        for (let j = 0; j < 5; j++)
          assetsData[asset][`protocol_${j}`] = createTestBalance(10, 0);
      }

      const largeBalances = assetsData;
      const largePrices: Record<string, any> = {};
      for (const [asset, priceData] of Object.entries(pricesData))
        largePrices[asset] = createTestPriceInfo(priceData.value, priceData.oracle);

      const startTime = performance.now();
      const result = updateBalancesPrices(largeBalances, largePrices);
      const endTime = performance.now();

      expect(endTime - startTime).toBeLessThan(100); // Should complete in less than 100ms
      expect(Object.keys(result)).toHaveLength(1000);
      expect(result.ASSET_0.protocol_0.value).toEqual(bigNumberify(1000));
    });
  });
});
