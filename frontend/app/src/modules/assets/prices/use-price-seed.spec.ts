import type { Balances } from '@/modules/accounts/blockchain-accounts';
import { bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePriceSeed } from '@/modules/assets/prices/use-price-seed';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBlockchainRefreshTimestampsStore } from '@/modules/balances/use-blockchain-refresh-timestamps-store';
import '@test/i18n';

const adjustPricesMock = vi.fn();
const queryOnlyCacheHistoricalRatesMock = vi.fn();

vi.mock('@/modules/balances/api/use-price-api', () => ({
  usePriceApi: vi.fn(() => ({
    queryOnlyCacheHistoricalRates: queryOnlyCacheHistoricalRatesMock,
  })),
}));

vi.mock('@/modules/assets/prices/use-price-refresh', () => ({
  usePriceRefresh: vi.fn(() => ({
    adjustPrices: adjustPricesMock,
  })),
}));

function seedBalances(balances: Balances): void {
  const balancesStore = useBalancesStore();
  const { balances: blockchainBalances } = storeToRefs(balancesStore);
  set(blockchainBalances, balances);
}

function seedTimestamps(timestamps: Record<string, number>): void {
  const { updateTimestamps } = useBlockchainRefreshTimestampsStore();
  updateTimestamps(timestamps);
}

describe('usePriceSeed', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    queryOnlyCacheHistoricalRatesMock.mockReset();
    adjustPricesMock.mockReset();
  });

  it('should not call the api when no chain timestamps are present', async () => {
    const { seedFromHistoric } = usePriceSeed();
    await seedFromHistoric();

    expect(queryOnlyCacheHistoricalRatesMock).not.toHaveBeenCalled();
    expect(adjustPricesMock).not.toHaveBeenCalled();
  });

  it('should not call the api when timestamps exist but no balances are loaded', async () => {
    seedTimestamps({ eth: 1700000000 });

    const { seedFromHistoric } = usePriceSeed();
    await seedFromHistoric();

    expect(queryOnlyCacheHistoricalRatesMock).not.toHaveBeenCalled();
  });

  it('should query and seed prices for assets held on a single chain', async () => {
    seedBalances({
      eth: {
        '0xaccount': {
          assets: {
            ETH: { amount: bigNumberify(1), value: bigNumberify(1500) },
            DAI: { amount: bigNumberify(100), value: bigNumberify(100) },
          } as any,
          liabilities: {} as any,
        },
      },
    });
    seedTimestamps({ eth: 1700000000 });

    queryOnlyCacheHistoricalRatesMock.mockResolvedValue({
      assets: {
        ETH: { 1700000000: '1500.00' },
        DAI: { 1700000000: '1.00' },
      },
      targetAsset: 'USD',
    });

    const { seedFromHistoric } = usePriceSeed();
    await seedFromHistoric();

    expect(queryOnlyCacheHistoricalRatesMock).toHaveBeenCalledTimes(1);
    const payload = queryOnlyCacheHistoricalRatesMock.mock.calls[0][0];
    expect(payload.targetAsset).toBe('USD');
    expect(payload.onlyCachePeriod).toBe(6 * 60 * 60);
    expect(payload.assetsTimestamp).toEqual(expect.arrayContaining([
      ['ETH', '1700000000'],
      ['DAI', '1700000000'],
    ]));

    const { prices } = storeToRefs(useBalancePricesStore());
    expect(get(prices)).toEqual({
      ETH: { isManualPrice: false, oracle: '', value: '1500.00' },
      DAI: { isManualPrice: false, oracle: '', value: '1.00' },
    });
    expect(adjustPricesMock).toHaveBeenCalledTimes(1);
  });

  it('should pick the newest timestamp for assets held on multiple chains', async () => {
    seedBalances({
      eth: {
        '0xa': {
          assets: { USDC: { amount: bigNumberify(10), value: bigNumberify(10) } } as any,
          liabilities: {} as any,
        },
      },
      optimism: {
        '0xb': {
          assets: { USDC: { amount: bigNumberify(20), value: bigNumberify(20) } } as any,
          liabilities: {} as any,
        },
      },
    });
    seedTimestamps({ eth: 1700000000, optimism: 1700100000 });

    queryOnlyCacheHistoricalRatesMock.mockResolvedValue({
      assets: { USDC: { 1700100000: '1.00' } },
      targetAsset: 'USD',
    });

    const { seedFromHistoric } = usePriceSeed();
    await seedFromHistoric();

    const payload = queryOnlyCacheHistoricalRatesMock.mock.calls[0][0];
    expect(payload.assetsTimestamp).toEqual([['USDC', '1700100000']]);
  });

  it('should include liability assets in the seed query', async () => {
    seedBalances({
      eth: {
        '0xa': {
          assets: {} as any,
          liabilities: { DAI: { amount: bigNumberify(50), value: bigNumberify(50) } } as any,
        },
      },
    });
    seedTimestamps({ eth: 1700000000 });

    queryOnlyCacheHistoricalRatesMock.mockResolvedValue({
      assets: { DAI: { 1700000000: '1.00' } },
      targetAsset: 'USD',
    });

    const { seedFromHistoric } = usePriceSeed();
    await seedFromHistoric();

    const payload = queryOnlyCacheHistoricalRatesMock.mock.calls[0][0];
    expect(payload.assetsTimestamp).toEqual([['DAI', '1700000000']]);
  });

  it('should swallow api errors without throwing or mutating the store', async () => {
    seedBalances({
      eth: {
        '0xa': {
          assets: { ETH: { amount: bigNumberify(1), value: bigNumberify(1500) } } as any,
          liabilities: {} as any,
        },
      },
    });
    seedTimestamps({ eth: 1700000000 });

    queryOnlyCacheHistoricalRatesMock.mockRejectedValue(new Error('boom'));

    const { seedFromHistoric } = usePriceSeed();
    await expect(seedFromHistoric()).resolves.toBeUndefined();

    expect(adjustPricesMock).not.toHaveBeenCalled();
    const { prices } = storeToRefs(useBalancePricesStore());
    expect(get(prices)).toEqual({});
  });

  it('should not update the store when the api returns no prices', async () => {
    seedBalances({
      eth: {
        '0xa': {
          assets: { ETH: { amount: bigNumberify(1), value: bigNumberify(1500) } } as any,
          liabilities: {} as any,
        },
      },
    });
    seedTimestamps({ eth: 1700000000 });

    queryOnlyCacheHistoricalRatesMock.mockResolvedValue({ assets: {}, targetAsset: 'USD' });

    const { seedFromHistoric } = usePriceSeed();
    await seedFromHistoric();

    expect(adjustPricesMock).not.toHaveBeenCalled();
  });
});
