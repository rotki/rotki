import { bigNumberify, Zero } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type PoolBalances, PoolType } from './types';
import { usePoolBalances } from './use-pool-balances';
import { usePoolBalancesStore } from './use-pool-balances-store';
import '@test/i18n';

const mockFetch = vi.fn();
const mockGetAssetField = vi.fn();

vi.mock('./use-pool-data-fetching', () => ({
  usePoolDataFetching: vi.fn((): Record<string, unknown> => ({
    fetch: mockFetch,
  })),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn((): Record<string, unknown> => ({
    getAssetField: mockGetAssetField,
  })),
}));

function makePoolBalance(address: string, value: string, assets: Array<{ asset: string; value: string }>): PoolBalances[string][number] {
  return {
    address,
    assets: assets.map(a => ({
      asset: a.asset,
      totalAmount: null,
      userBalance: { amount: bigNumberify(a.value), value: bigNumberify(a.value) },
    })),
    userBalance: { amount: bigNumberify(value), value: bigNumberify(value) },
  };
}

function setStoreData(data: { uniswap?: PoolBalances; sushiswap?: PoolBalances }): void {
  const store = usePoolBalancesStore();
  store.$patch({
    ...(data.uniswap && { uniswapPoolBalances: data.uniswap }),
    ...(data.sushiswap && { sushiswapPoolBalances: data.sushiswap }),
  });
}

describe('usePoolBalances', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockFetch.mockResolvedValue(undefined);
    mockGetAssetField.mockImplementation((asset: string): string => asset.toUpperCase());
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('balances', () => {
    it('should return empty when no pool data', () => {
      const { balances } = usePoolBalances();
      expect(get(balances)).toEqual([]);
    });

    it('should aggregate and sort balances by value descending', () => {
      setStoreData({
        uniswap: {
          '0xAccount1': [
            makePoolBalance('0xPool1', '100', [{ asset: 'ETH', value: '50' }, { asset: 'DAI', value: '50' }]),
            makePoolBalance('0xPool2', '200', [{ asset: 'USDC', value: '200' }]),
          ],
        },
      });

      const { balances } = usePoolBalances();
      const result = get(balances);

      expect(result).toHaveLength(2);
      // Sorted descending: Pool2 (200) before Pool1 (100)
      expect(result[0].value).toEqual(bigNumberify('200'));
      expect(result[1].value).toEqual(bigNumberify('100'));
      // IDs reassigned after sort
      expect(result[0].id).toBe(0);
      expect(result[1].id).toBe(1);
    });

    it('should aggregate same pool address across accounts', () => {
      setStoreData({
        uniswap: {
          '0xAccount1': [makePoolBalance('0xPool1', '100', [{ asset: 'ETH', value: '50' }])],
          '0xAccount2': [makePoolBalance('0xPool1', '300', [{ asset: 'ETH', value: '150' }])],
        },
      });

      const { balances } = usePoolBalances();
      const result = get(balances);

      expect(result).toHaveLength(1);
      // Aggregated: 100 + 300 = 400
      expect(result[0].value).toEqual(bigNumberify('400'));
    });

    it('should mark uniswap as not premium and sushiswap as premium', () => {
      setStoreData({
        uniswap: { '0xA': [makePoolBalance('0xPool1', '100', [{ asset: 'ETH', value: '100' }])] },
        sushiswap: { '0xA': [makePoolBalance('0xPool2', '200', [{ asset: 'DAI', value: '200' }])] },
      });

      const { balances } = usePoolBalances();
      const result = get(balances);

      const uniswap = result.find(b => b.type === PoolType.UNISWAP_V2);
      const sushiswap = result.find(b => b.type === PoolType.SUSHISWAP);
      expect(uniswap?.premiumOnly).toBe(false);
      expect(sushiswap?.premiumOnly).toBe(true);
    });
  });

  describe('total', () => {
    it('should return zero when no balances', () => {
      const { total } = usePoolBalances();
      expect(get(total)).toEqual(Zero);
    });

    it('should sum all balance values', () => {
      setStoreData({
        uniswap: {
          '0xA': [
            makePoolBalance('0xPool1', '100', []),
            makePoolBalance('0xPool2', '250', []),
          ],
        },
      });

      const { total } = usePoolBalances();
      expect(get(total)).toEqual(bigNumberify('350'));
    });
  });

  describe('getPoolName', () => {
    it('should format uniswap pool name', () => {
      const { getPoolName } = usePoolBalances();
      const name = getPoolName(PoolType.UNISWAP_V2, ['ETH', 'DAI']);
      expect(name).toBe('UNI-V2 ETH-DAI');
    });

    it('should format sushiswap pool name', () => {
      const { getPoolName } = usePoolBalances();
      const name = getPoolName(PoolType.SUSHISWAP, ['WETH', 'USDC']);
      expect(name).toBe('SLP WETH-USDC');
    });

    it('should fallback to concatenated assets for unknown type', () => {
      const { getPoolName } = usePoolBalances();
      // @ts-expect-error testing fallback with invalid enum value
      const name = getPoolName('unknown', ['ETH', 'DAI']);
      expect(name).toBe('ETH-DAI');
    });
  });

  describe('fetch', () => {
    it('should delegate to usePoolDataFetching', async () => {
      const { fetch } = usePoolBalances();
      await fetch(true);
      expect(mockFetch).toHaveBeenCalledWith(true);
    });
  });
});
