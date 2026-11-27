import type { HistoricalBalanceEntry, HistoricalBalanceSeriesResponse } from '@/modules/history/balances/types';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import {
  alignBuckets,
  type BalancePoint,
  type BucketSeries,
  buildBucketSeries,
  summarize,
  totalSeries,
} from './balance-series';

type SeriesEntry = HistoricalBalanceSeriesResponse['entries'][number];

function series(location: string, protocol: string | null, points: [number, string][]): SeriesEntry {
  return {
    asset: 'ETH',
    location,
    locationLabel: '0xA',
    protocol,
    times: points.map(([time]) => time),
    values: points.map(([, value]) => bigNumberify(value)),
  };
}

function opening(location: string, protocol: string | null, amount: string): HistoricalBalanceEntry {
  return { amount: bigNumberify(amount), asset: 'ETH', location, locationLabel: '0xA', protocol };
}

function plain(points: readonly BalancePoint[]): [number, string][] {
  return points.map(({ time, value }) => [time, value.toString()]);
}

function bucket(location: string, protocol: string | undefined, points: [number, string][]): BucketSeries {
  return {
    key: `${location}:${protocol ?? ''}`,
    location,
    points: points.map(([time, value]) => ({ time, value: bigNumberify(value) })),
    protocol,
  };
}

describe('buildBucketSeries', () => {
  it('should start each bucket at its balance before the range and carry it to the range end', () => {
    const [eth] = buildBucketSeries(
      [opening('ethereum', null, '5')],
      [series('ethereum', null, [[150, '7']])],
      { from: 100, to: 300 },
    );

    expect(plain(eth?.points ?? [])).toEqual([[100, '5'], [150, '7'], [300, '7']]);
  });

  it('should draw a bucket without events in the range as a flat line at its opening balance', () => {
    const [aave] = buildBucketSeries([opening('ethereum', 'aave', '2')], [], { from: 100, to: 300 });

    expect(aave?.protocol).toBe('aave');
    expect(plain(aave?.points ?? [])).toEqual([[100, '2'], [300, '2']]);
  });

  it('should keep only the balance after the last event of a second', () => {
    const [eth] = buildBucketSeries([], [series('ethereum', null, [[100, '1'], [100, '3'], [200, '4']])], { from: 0, to: 200 });

    expect(plain(eth?.points ?? [])).toEqual([[100, '3'], [200, '4']]);
  });

  it('should keep a balance that dropped to zero', () => {
    const [eth] = buildBucketSeries([], [series('ethereum', null, [[100, '2'], [200, '0'], [300, '1']])], { from: 0, to: 400 });

    expect(plain(eth?.points ?? [])).toEqual([[100, '2'], [200, '0'], [300, '1'], [400, '1']]);
  });

  it('should split buckets by location and protocol, in a stable order', () => {
    const buckets = buildBucketSeries([], [
      series('optimism', null, [[100, '1']]),
      series('ethereum', 'aave', [[100, '1']]),
      series('ethereum', null, [[100, '1']]),
    ], { from: 0, to: 100 });

    expect(buckets.map(({ key }) => key)).toEqual(['ethereum:', 'ethereum:aave', 'optimism:']);
  });
});

describe('alignBuckets', () => {
  it('should give every bucket a value at every time, zero before its first point', () => {
    const { rows, times } = alignBuckets([
      bucket('ethereum', undefined, [[100, '1'], [300, '2']]),
      bucket('ethereum', 'aave', [[200, '5']]),
    ]);

    expect(times).toEqual([100, 200, 300]);
    expect(rows.map(row => row.map(value => value.toString()))).toEqual([['1', '1', '2'], ['0', '5', '5']]);
  });
});

describe('totalSeries', () => {
  it('should add up the latest value of each bucket at every change', () => {
    const total = totalSeries([
      bucket('ethereum', undefined, [[100, '1'], [300, '2']]),
      bucket('ethereum', 'aave', [[200, '5'], [300, '0']]),
    ]);

    expect(plain(total)).toEqual([[100, '1'], [200, '6'], [300, '2']]);
  });

  it('should be empty without buckets', () => {
    expect(totalSeries([])).toEqual([]);
  });
});

describe('summarize', () => {
  it('should measure the change from the balance held at the range start', () => {
    const summary = summarize([{ time: 100, value: bigNumberify(5) }, { time: 300, value: bigNumberify(8) }], 100);

    expect(summary.start.toString()).toBe('5');
    expect(summary.current.toString()).toBe('8');
    expect(summary.change.toString()).toBe('3');
  });

  it('should start from zero when the first balance comes after the range start', () => {
    const summary = summarize([{ time: 150, value: bigNumberify(5) }, { time: 300, value: bigNumberify(2) }], 100);

    expect(summary.start.toString()).toBe('0');
    expect(summary.change.toString()).toBe('2');
  });

  it('should read an empty series as zero throughout', () => {
    const summary = summarize([], 0);

    expect(summary.current.isZero()).toBe(true);
    expect(summary.change.isZero()).toBe(true);
  });
});
