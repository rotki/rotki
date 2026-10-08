import type { HistoricalBucket } from './historical-balances-grouping';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { filterRows, HistoricalBalancesMode, sortRows, summarize, toViewRows } from './historical-balances-view';
import { type HistoricalAssetRow, PriceStatus } from './use-historical-balance-values';

function bucket(location: string, locationLabel: string | null, amount: string): HistoricalBucket {
  return { amount: bigNumberify(amount), location, locationLabel, protocol: null };
}

function row(asset: string, buckets: HistoricalBucket[], price?: string, unpriced: PriceStatus = PriceStatus.MISSING): HistoricalAssetRow {
  const amount = buckets.reduce((sum, { amount }) => sum.plus(amount), bigNumberify(0));
  return {
    amount,
    asset,
    buckets,
    price: price ? bigNumberify(price) : undefined,
    priceStatus: price ? PriceStatus.PRICED : unpriced,
    value: price ? amount.times(price) : undefined,
  };
}

const NO_FILTER = { accounts: [], locations: [] };

const COLLECTIONS: Record<string, string> = {
  'eip155:1/erc20:0xUSDC': 'usdc',
  'eip155:42161/erc20:0xUSDC': 'usdc',
  'eip155:10/erc20:0xUSDC': 'usdc',
};

const lookup = {
  collectionOf: (asset: string): string | undefined => COLLECTIONS[asset],
  mainAssetOf: (collectionId: string): string | undefined => (collectionId === 'usdc' ? 'eip155:1/erc20:0xUSDC' : undefined),
};

describe('filterRows', () => {
  it('should keep only the buckets on the chosen locations, and recompute amount and value from them', () => {
    const rows = [row('ETH', [bucket('ethereum', '0xA', '1'), bucket('arbitrum_one', '0xA', '2')], '1000')];

    const [filtered] = filterRows(rows, { ...NO_FILTER, locations: ['arbitrum_one'] });

    expect(filtered.buckets.map(({ location }) => location)).toEqual(['arbitrum_one']);
    expect(filtered.amount.toString()).toBe('2');
    expect(filtered.value?.toString()).toBe('2000');
  });

  it('should drop a row left with no buckets', () => {
    const rows = [row('ETH', [bucket('ethereum', '0xA', '1')], '1000'), row('BTC', [bucket('bitcoin', 'bc1', '1')], '50000')];

    expect(filterRows(rows, { ...NO_FILTER, locations: ['bitcoin'] }).map(({ asset }) => asset)).toEqual(['BTC']);
  });

  it('should never match a bucket without an account when filtering by account', () => {
    const rows = [row('ETH', [bucket('external', null, '5'), bucket('ethereum', '0xA', '1')], '1000')];

    const [filtered] = filterRows(rows, { ...NO_FILTER, accounts: ['0xA'] });

    expect(filtered.buckets).toHaveLength(1);
    expect(filtered.amount.toString()).toBe('1');
  });

  it('should require a bucket to match both the location and the account', () => {
    const rows = [row('ETH', [bucket('ethereum', '0xA', '1'), bucket('optimism', '0xA', '2'), bucket('ethereum', '0xB', '4')], '1')];

    const [filtered] = filterRows(rows, { accounts: ['0xA'], locations: ['ethereum'] });

    expect(filtered.amount.toString()).toBe('1');
  });

  it('should keep assets the matcher accepts, with their rows untouched', () => {
    const eth = row('ETH', [bucket('ethereum', '0xA', '1')], '1000');
    const rows = [eth, row('DAI', [bucket('ethereum', '0xA', '1')], '1')];

    expect(filterRows(rows, { ...NO_FILTER, matchesAsset: asset => asset === 'ETH' })).toEqual([eth]);
  });

  it('should leave an unpriced row without a value', () => {
    const rows = [row('RARE', [bucket('ethereum', '0xA', '1'), bucket('base', '0xA', '1')])];

    const [filtered] = filterRows(rows, { ...NO_FILTER, locations: ['base'] });

    expect(filtered.value).toBeUndefined();
    expect(filtered.priceStatus).toBe(PriceStatus.MISSING);
  });
});

describe('summarize', () => {
  it('should total the priced rows and count the rest by why they have no value', () => {
    const summary = summarize([
      row('ETH', [bucket('ethereum', '0xA', '1')], '1000'),
      row('DAI', [bucket('ethereum', '0xA', '5')], '1'),
      row('RARE', [bucket('ethereum', '0xA', '1')]),
      row('SCAM', [bucket('ethereum', '0xA', '1')], undefined, PriceStatus.SPAM),
      row('NEW', [bucket('ethereum', '0xA', '1')], undefined, PriceStatus.PENDING),
    ]);

    expect(summary.total.toString()).toBe('1005');
    expect(summary).toMatchObject({ missingCount: 1, pendingCount: 1, spamCount: 1 });
  });
});

describe('toViewRows', () => {
  const usdcMainnet = row('eip155:1/erc20:0xUSDC', [bucket('ethereum', '0xA', '100')], '0.9');
  const usdcArbitrum = row('eip155:42161/erc20:0xUSDC', [bucket('arbitrum_one', '0xA', '300')], '0.95');

  it('should fold a collection into one row headed by its main asset, valuing each member at its own price', () => {
    const [folded] = toViewRows([usdcArbitrum, usdcMainnet], HistoricalBalancesMode.COLLECTION, lookup);

    expect(folded.asset).toBe('eip155:1/erc20:0xUSDC');
    expect(folded.members).toEqual(['eip155:42161/erc20:0xUSDC', 'eip155:1/erc20:0xUSDC']);
    expect(folded.amount.toString()).toBe('400');
    expect(folded.value?.toString()).toBe('375');
    expect(folded.price?.toString()).toBe('0.9375');
    expect(folded.partial).toBe(false);
  });

  it('should list every member\'s buckets in the folded row, largest first, each at its own value', () => {
    const [folded] = toViewRows([usdcMainnet, usdcArbitrum], HistoricalBalancesMode.COLLECTION, lookup);

    expect(folded.buckets.map(({ asset, value }) => [asset, value?.toString()])).toEqual([
      ['eip155:42161/erc20:0xUSDC', '285'],
      ['eip155:1/erc20:0xUSDC', '90'],
    ]);
  });

  it('should head a collection by its main asset even when the main asset holds nothing', () => {
    const usdcOptimism = row('eip155:10/erc20:0xUSDC', [bucket('optimism', '0xA', '1')], '1');

    const [folded] = toViewRows([usdcArbitrum, usdcOptimism], HistoricalBalancesMode.COLLECTION, lookup);

    expect(folded.asset).toBe('eip155:1/erc20:0xUSDC');
  });

  it('should keep a collection with a single member held as that member\'s own row', () => {
    const rows = toViewRows([usdcArbitrum], HistoricalBalancesMode.COLLECTION, lookup);

    expect(rows.map(({ asset, members }) => [asset, members])).toEqual([['eip155:42161/erc20:0xUSDC', ['eip155:42161/erc20:0xUSDC']]]);
  });

  it('should keep members apart while their collection\'s main asset is not known', () => {
    const rows = toViewRows([usdcArbitrum, usdcMainnet], HistoricalBalancesMode.COLLECTION, { ...lookup, mainAssetOf: () => undefined });

    expect(rows).toHaveLength(2);
  });

  it('should mark a collection whose members are only partly priced, valuing the priced ones', () => {
    const unpriced = row('eip155:10/erc20:0xUSDC', [bucket('optimism', '0xA', '50')]);

    const [folded] = toViewRows([usdcMainnet, unpriced], HistoricalBalancesMode.COLLECTION, lookup);

    expect(folded.priceStatus).toBe(PriceStatus.PRICED);
    expect(folded.partial).toBe(true);
    expect(folded.value?.toString()).toBe('90');
    expect(folded.price?.toString()).toBe('0.9');
  });

  it('should keep a collection pending while any member\'s price is', () => {
    const pending = row('eip155:10/erc20:0xUSDC', [bucket('optimism', '0xA', '50')], undefined, PriceStatus.PENDING);

    const [folded] = toViewRows([usdcMainnet, pending], HistoricalBalancesMode.COLLECTION, lookup);

    expect(folded.priceStatus).toBe(PriceStatus.PENDING);
    expect(folded.value).toBeUndefined();
  });

  it('should show one row per asset in flat mode', () => {
    const rows = toViewRows([usdcArbitrum, usdcMainnet], HistoricalBalancesMode.FLAT, lookup);

    expect(rows.map(({ asset }) => asset)).toEqual(['eip155:42161/erc20:0xUSDC', 'eip155:1/erc20:0xUSDC']);
  });
});

describe('sortRows', () => {
  it('should put priced rows first by value, then pending, missing and spam rows by amount', () => {
    const rows = toViewRows([
      row('SCAM', [bucket('ethereum', '0xA', '900000')], undefined, PriceStatus.SPAM),
      row('RARE', [bucket('ethereum', '0xA', '5')]),
      row('DAI', [bucket('ethereum', '0xA', '10')], '1'),
      row('NEW', [bucket('ethereum', '0xA', '1')], undefined, PriceStatus.PENDING),
      row('ETH', [bucket('ethereum', '0xA', '1')], '2000'),
    ], HistoricalBalancesMode.FLAT, lookup);

    expect(sortRows(rows).map(({ asset }) => asset)).toEqual(['ETH', 'DAI', 'NEW', 'RARE', 'SCAM']);
  });
});
