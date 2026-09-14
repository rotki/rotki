import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { mergeSameScopeBuckets, type PreparedBucket, valueAt } from './accounting-overlay-helpers';

function bucket(protocol: string | null, times: number[], values: string[], location = 'ethereum'): PreparedBucket {
  return { location, protocol, times, values: values.map(value => bigNumberify(value)) };
}

describe('valueAt', () => {
  it('should read zero for an empty series or before its first point', () => {
    expect(valueAt(bucket(null, [], []), 100).toString()).toBe('0');
    expect(valueAt(bucket(null, [100, 200], ['1', '3']), 99).toString()).toBe('0');
  });

  it('should hold the latest value at or before the timestamp', () => {
    const series = bucket(null, [100, 200, 300], ['1', '3', '2']);
    expect([100, 150, 200, 250, 999].map(tsSec => valueAt(series, tsSec).toString())).toEqual(['1', '1', '3', '3', '2']);
  });
});

describe('mergeSameScopeBuckets', () => {
  it('should merge null and empty protocol series into one wallet bucket instead of double-counting', () => {
    const [merged, ...rest] = mergeSameScopeBuckets([
      bucket(null, [100, 200], ['10', '4']),
      bucket('', [300, 400], ['50', '60']),
    ]);

    expect(rest).toHaveLength(0);
    expect(merged.protocol).toBeNull();
    expect(merged.times).toEqual([100, 200, 300, 400]);
    expect(valueAt(merged, 500).toString()).toBe('60');
    expect(valueAt(merged, 250).toString()).toBe('4');
  });

  it('should let the later entry win when two series of one scope share a timestamp', () => {
    const [merged] = mergeSameScopeBuckets([
      bucket(null, [100, 200], ['1', '2']),
      bucket('', [200, 300], ['5', '6']),
    ]);

    expect(merged.times).toEqual([100, 200, 300]);
    expect(merged.values.map(value => value.toString())).toEqual(['1', '5', '6']);
  });

  it('should keep different chains and protocols apart without mutating the input', () => {
    const input = [
      bucket(null, [100], ['1']),
      bucket('aave-v3', [100], ['2']),
      bucket(null, [100], ['3'], 'base'),
    ];
    const result = mergeSameScopeBuckets(input);

    expect(result.map(entry => [entry.location, entry.protocol])).toEqual([['ethereum', null], ['ethereum', 'aave-v3'], ['base', null]]);
    result[0].times.push(999);
    expect(input[0].times).toEqual([100]);
  });
});
