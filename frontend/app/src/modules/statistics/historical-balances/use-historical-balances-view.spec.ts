import type { HistoricalBucket } from './historical-balances-grouping';
import { bigNumberify } from '@rotki/common';
import { get, set } from '@vueuse/shared';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope, nextTick } from 'vue';
import { HistoricalBalancesMode } from './historical-balances-view';
import { type HistoricalAssetRow, PriceStatus } from './use-historical-balance-values';
import { useHistoricalBalancesView } from './use-historical-balances-view';

const INFO: Record<string, { symbol: string; name: string }> = {
  'eip155:1/erc20:0xUSDC': { name: 'USD Coin', symbol: 'USDC' },
  'eip155:10/erc20:0xUSDC': { name: 'USD Coin', symbol: 'USDC' },
  'ETH': { name: 'Ether', symbol: 'ETH' },
};

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): Record<string, unknown> => ({ getAssetInfo: (asset: string): unknown => INFO[asset] ?? null }),
}));
vi.mock('@/modules/assets/use-collection-info', () => ({
  useCollectionInfo: (): Record<string, unknown> => ({
    getCollectionId: (asset: string): string | undefined => (asset.endsWith('0xUSDC') ? 'usdc' : undefined),
    getCollectionMainAsset: (): string => 'eip155:1/erc20:0xUSDC',
  }),
}));

function bucket(location: string, locationLabel: string | null, amount = '1'): HistoricalBucket {
  return { amount: bigNumberify(amount), location, locationLabel, protocol: null };
}

function row(asset: string, buckets: HistoricalBucket[]): HistoricalAssetRow {
  const amount = buckets.reduce((sum, item) => sum.plus(item.amount), bigNumberify(0));
  return { amount, asset, buckets, price: bigNumberify('1'), priceStatus: PriceStatus.PRICED, value: amount };
}

const ROWS = [
  row('ETH', [bucket('ethereum', '0xA', '2'), bucket('kraken', 'Kraken 1', '3')]),
  row('eip155:1/erc20:0xUSDC', [bucket('ethereum', '0xA', '10')]),
  row('eip155:10/erc20:0xUSDC', [bucket('optimism', '0xA', '20'), bucket('external', null, '5')]),
];

let scope: EffectScope;

function create(): ReturnType<typeof useHistoricalBalancesView> {
  const view = scope.run(() => useHistoricalBalancesView(ROWS));
  assert(view);
  return view;
}

describe('useHistoricalBalancesView', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    scope = effectScope();
  });

  afterEach(() => {
    scope.stop();
    vi.useRealTimers();
  });

  it('should fold collections by default', () => {
    const view = create();

    expect(get(view.modelMode)).toBe(HistoricalBalancesMode.COLLECTION);
    expect(get(view.rows).map(({ asset }) => asset).sort()).toEqual(['ETH', 'eip155:1/erc20:0xUSDC']);
  });

  it('should offer every location and every account of the day, each once', () => {
    const view = create();

    expect(get(view.locations)).toEqual(['ethereum', 'external', 'kraken', 'optimism']);
    expect(get(view.accounts)).toEqual(['0xA', 'Kraken 1']);
  });

  it('should total only what the filter keeps', async () => {
    const view = create();
    expect(get(view.summary).total.toString()).toBe('40');

    set(view.modelLocations, ['ethereum']);
    await nextTick();

    expect(get(view.summary).total.toString()).toBe('12');
    expect(get(view.filtered)).toBe(true);
  });

  it('should find an asset by its symbol or name once the search settles', async () => {
    const view = create();

    set(view.modelSearch, 'usd coin');
    await vi.advanceTimersByTimeAsync(250);

    expect(get(view.rows).map(({ asset }) => asset)).toEqual(['eip155:1/erc20:0xUSDC']);
    expect(get(view.summary).total.toString()).toBe('35');
  });

  it('should keep the total the same in either mode', async () => {
    const view = create();
    const total = get(view.summary).total.toString();

    set(view.modelMode, HistoricalBalancesMode.FLAT);
    await nextTick();

    expect(get(view.rows)).toHaveLength(3);
    expect(get(view.summary).total.toString()).toBe(total);
  });
});
