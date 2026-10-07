import type { HistoricalAssetGroup } from './historical-balances-grouping';
import { type BigNumber, bigNumberify, NoPrice } from '@rotki/common';
import { get } from '@vueuse/shared';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ComputedRef, type EffectScope, effectScope, nextTick } from 'vue';
import { type HistoricalBalancesSummary, summarize } from './historical-balances-view';
import { PRICE_BATCH_SIZE, PriceStatus, useHistoricalBalanceValues } from './use-historical-balance-values';

interface InfoStub { isSpam?: boolean; resolved: boolean }

const { getHistoricPrice, infoPending, infos, pricePending, prices } = await vi.hoisted(async () => {
  const { reactive } = await import('vue');
  return {
    getHistoricPrice: vi.fn<(asset: string, timestamp: number) => BigNumber>(),
    infoPending: reactive(new Set<string>()),
    infos: reactive(new Map<string, InfoStub>()),
    pricePending: reactive(new Set<string>()),
    prices: reactive(new Map<string, string>()),
  };
});

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: (): Record<string, unknown> => ({
    createKey: (asset: string, timestamp: number): string => `${asset}#${timestamp}`,
    getHistoricPrice,
    getIsPending: (key: string): boolean => pricePending.has(key),
  }),
}));
vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): Record<string, unknown> => ({
    getAssetInfo: (asset: string): InfoStub | null => infos.get(asset) ?? null,
  }),
}));
vi.mock('@/modules/assets/use-asset-info-cache', async () => {
  const { computed } = await import('vue');
  return {
    useAssetInfoCache: (): Record<string, unknown> => ({
      isPending: (asset: string): ComputedRef<boolean> => computed<boolean>(() => infoPending.has(asset)),
    }),
  };
});

function group(asset: string, amount = '1'): HistoricalAssetGroup {
  return { amount: bigNumberify(amount), asset, buckets: [] };
}

function known(asset: string, price?: string, isSpam = false): HistoricalAssetGroup {
  infos.set(asset, { isSpam, resolved: true });
  if (price)
    prices.set(asset, price);
  return group(asset);
}

let scope: EffectScope;

function create(groups: HistoricalAssetGroup[]): ReturnType<typeof useHistoricalBalanceValues> {
  const values = scope.run(() => useHistoricalBalanceValues(groups, 100));
  assert(values);
  return values;
}

function statusOf(values: ReturnType<typeof useHistoricalBalanceValues>, asset: string): string | undefined {
  return get(values.rows).find(row => row.asset === asset)?.priceStatus;
}

function summaryOf(values: ReturnType<typeof useHistoricalBalanceValues>): HistoricalBalancesSummary {
  return summarize(get(values.rows));
}

describe('useHistoricalBalanceValues', () => {
  beforeEach(() => {
    scope = effectScope();
    infoPending.clear();
    infos.clear();
    pricePending.clear();
    prices.clear();
    getHistoricPrice.mockReset().mockImplementation((asset) => {
      const price = prices.get(asset);
      return price ? bigNumberify(price) : NoPrice;
    });
  });

  afterEach(() => scope.stop());

  it('should value each asset at its price at the as-of time', async () => {
    const values = create([known('ETH', '2000')]);
    await nextTick();

    expect(get(values.rows)[0].value?.toString()).toBe('2000');
    expect(summaryOf(values).total.toString()).toBe('2000');
    expect(getHistoricPrice).toHaveBeenCalledWith('ETH', 100);
  });

  it('should never price a spam asset, and count it apart from the total', async () => {
    const values = create([known('ETH', '2000'), known('SCAM', undefined, true)]);
    await nextTick();

    expect(statusOf(values, 'SCAM')).toBe(PriceStatus.SPAM);
    expect(getHistoricPrice).not.toHaveBeenCalledWith('SCAM', expect.any(Number));
    expect(summaryOf(values).spamCount).toBe(1);
    expect(summaryOf(values).total.toString()).toBe('2000');
  });

  it('should hold an asset back until its info says whether it is spam', async () => {
    infoPending.add('NEW');
    const values = create([group('NEW')]);
    await nextTick();

    expect(getHistoricPrice).not.toHaveBeenCalled();
    expect(statusOf(values, 'NEW')).toBe(PriceStatus.PENDING);

    infoPending.delete('NEW');
    infos.set('NEW', { resolved: true });
    prices.set('NEW', '3');
    await nextTick();
    await nextTick();

    expect(statusOf(values, 'NEW')).toBe(PriceStatus.PRICED);
  });

  it('should price in batches, releasing the next once the current one settles', async () => {
    const assets = Array.from({ length: PRICE_BATCH_SIZE + 10 }, (_, i) => `A${i}`);
    for (const asset of assets)
      pricePending.add(`${asset}#100`);
    const values = create(assets.map(asset => known(asset, '1')));
    await nextTick();

    const asked = (): number => new Set(getHistoricPrice.mock.calls.map(([asset]) => asset)).size;
    expect(asked()).toBe(PRICE_BATCH_SIZE);

    for (const asset of assets.slice(0, PRICE_BATCH_SIZE))
      pricePending.delete(`${asset}#100`);
    await nextTick();
    await nextTick();

    expect(asked()).toBe(assets.length);
    expect(summaryOf(values).pendingCount).toBe(10);
  });

  it('should count an asset whose price settled empty as missing, not pending', async () => {
    const values = create([known('RARE')]);
    await nextTick();

    expect(statusOf(values, 'RARE')).toBe(PriceStatus.MISSING);
    expect(summaryOf(values).missingCount).toBe(1);
    expect(summaryOf(values).pendingCount).toBe(0);
  });
});
