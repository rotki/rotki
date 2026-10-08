import type { HistoricalBalanceEntry } from '@/modules/history/balances/types';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { groupByAsset, type HistoricalAssetGroup } from './historical-balances-grouping';

function entry(asset: string, amount: string, overrides: Partial<HistoricalBalanceEntry> = {}): HistoricalBalanceEntry {
  return { amount: bigNumberify(amount), asset, location: 'ethereum', locationLabel: '0xA', protocol: null, ...overrides };
}

function plain(groups: HistoricalAssetGroup[]): unknown[] {
  return groups.map(group => ({
    amount: group.amount.toString(),
    asset: group.asset,
    buckets: group.buckets.map(bucket => ({ ...bucket, amount: bucket.amount.toString() })),
  }));
}

describe('groupByAsset', () => {
  it('should sum an asset across its buckets and order the buckets largest first', () => {
    const groups = groupByAsset([
      entry('ETH', '1', { locationLabel: '0xA' }),
      entry('ETH', '3', { location: 'kraken', locationLabel: 'main' }),
      entry('DAI', '50'),
    ]);

    expect(plain(groups)).toEqual([
      {
        amount: '4',
        asset: 'ETH',
        buckets: [
          { amount: '3', location: 'kraken', locationLabel: 'main', protocol: null },
          { amount: '1', location: 'ethereum', locationLabel: '0xA', protocol: null },
        ],
      },
      { amount: '50', asset: 'DAI', buckets: [{ amount: '50', location: 'ethereum', locationLabel: '0xA', protocol: null }] },
    ]);
  });

  it('should keep a protocol position apart from the same account\'s wallet', () => {
    const [eth] = groupByAsset([entry('ETH', '1'), entry('ETH', '2', { protocol: 'aave' })]);

    expect(eth.buckets.map(({ protocol }) => protocol)).toEqual(['aave', null]);
  });

  it('should read an empty protocol and account as missing and merge what then coincides', () => {
    const groups = groupByAsset([
      entry('ETH', '1', { protocol: '' }),
      entry('ETH', '2', { protocol: null }),
      entry('BTC', '1', { location: 'bitcoin', locationLabel: '' }),
    ]);

    expect(plain(groups)).toEqual([
      { amount: '3', asset: 'ETH', buckets: [{ amount: '3', location: 'ethereum', locationLabel: '0xA', protocol: null }] },
      { amount: '1', asset: 'BTC', buckets: [{ amount: '1', location: 'bitcoin', locationLabel: null, protocol: null }] },
    ]);
  });

  it('should return no groups for no entries', () => {
    expect(groupByAsset([])).toEqual([]);
  });
});
