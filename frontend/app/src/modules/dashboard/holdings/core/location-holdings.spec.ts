import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { type LocationHolding, type SourceContribution, SourceKind } from './holdings-types';
import { mergeLocations, narrowToKind, tileTarget } from './location-holdings';

const locations: Record<string, string> = { btc: 'bitcoin', eth: 'ethereum' };

function locationOfChain(chain: string): string | undefined {
  return locations[chain];
}

function chain(id: string, value: number, loading = false): SourceContribution {
  return { chain: id, kind: SourceKind.BLOCKCHAIN, loading, value: bigNumberify(value) };
}

function at(kind: typeof SourceKind.EXCHANGE | typeof SourceKind.BANK | typeof SourceKind.MANUAL, location: string, value: number): SourceContribution {
  return { kind, loading: false, location, value: bigNumberify(value) };
}

function summary(holdings: readonly LocationHolding[]): { key: string; kinds: string[]; value: string }[] {
  return holdings.map(holding => ({
    key: holding.place.key,
    kinds: holding.parts.map(part => part.kind),
    value: holding.value.toFixed(),
  }));
}

describe('mergeLocations', () => {
  it('should merge an exchange and a manual balance at the same location into one holding', () => {
    const merged = mergeLocations([at(SourceKind.EXCHANGE, 'kraken', 100), at(SourceKind.MANUAL, 'kraken', 20)], { locationOfChain });

    expect(summary(merged)).toEqual([{ key: 'kraken', kinds: ['exchange', 'manual'], value: '120' }]);
  });

  it('should fold a manual balance recorded at a chain location into that chain', () => {
    const merged = mergeLocations([chain('eth', 50), at(SourceKind.MANUAL, 'ethereum', 5)], { locationOfChain });

    expect(summary(merged)).toEqual([{ key: 'ethereum', kinds: ['blockchain', 'manual'], value: '55' }]);
    expect(merged[0].place.chain).toBe('eth');
  });

  it('should keep a chain the backend has no location for as its own holding', () => {
    const merged = mergeLocations([chain('eth', 50), chain('eth2', 64)], { locationOfChain });

    expect(summary(merged)).toEqual([
      { key: 'chain:eth2', kinds: ['blockchain'], value: '64' },
      { key: 'ethereum', kinds: ['blockchain'], value: '50' },
    ]);
    expect(merged[0].target).toEqual({ chain: 'eth2', type: 'chain' });
  });

  it('should list parts in the fixed kind order whatever the input order', () => {
    const merged = mergeLocations([
      at(SourceKind.MANUAL, 'ethereum', 1),
      at(SourceKind.EXCHANGE, 'ethereum', 1),
      chain('eth', 1),
    ], { locationOfChain });

    expect(merged[0].parts.map(part => part.kind)).toEqual(['blockchain', 'exchange', 'manual']);
  });

  it('should sort holdings by value, highest first', () => {
    const merged = mergeLocations([at(SourceKind.EXCHANGE, 'kraken', 10), chain('btc', 300), at(SourceKind.BANK, 'qonto', 40)], { locationOfChain });

    expect(merged.map(holding => holding.place.key)).toEqual(['bitcoin', 'qonto', 'kraken']);
  });

  it('should drop empty places unless they are still loading', () => {
    const merged = mergeLocations([chain('btc', 0), chain('eth', 0, true)], { locationOfChain });

    expect(summary(merged)).toEqual([{ key: 'ethereum', kinds: ['blockchain'], value: '0' }]);
    expect(merged[0].loading).toBe(true);
  });
});

describe('tileTarget', () => {
  const ethereum = { chain: 'eth', key: 'ethereum', location: 'ethereum' };
  const kraken = { chain: undefined, key: 'kraken', location: 'kraken' };

  it.each([
    { expected: { chain: 'eth', type: 'chain' }, kinds: [SourceKind.BLOCKCHAIN], place: ethereum },
    { expected: { location: 'kraken', type: 'exchange' }, kinds: [SourceKind.EXCHANGE], place: kraken },
    { expected: { type: 'bank' }, kinds: [SourceKind.BANK], place: { ...kraken, key: 'qonto', location: 'qonto' } },
    { expected: { location: 'kraken', type: 'manual' }, kinds: [SourceKind.MANUAL], place: kraken },
    { expected: { location: 'kraken', type: 'location' }, kinds: [SourceKind.EXCHANGE, SourceKind.MANUAL], place: kraken },
    { expected: { location: 'ethereum', type: 'location' }, kinds: [SourceKind.BLOCKCHAIN, SourceKind.MANUAL], place: ethereum },
  ])('should lead $kinds at $place.key to $expected.type', ({ expected, kinds, place }) => {
    expect(tileTarget(place, kinds)).toEqual(expected);
  });
});

describe('narrowToKind', () => {
  it('should keep only the holdings a kind contributes to, valued at that part and re-sorted', () => {
    const merged = mergeLocations([
      at(SourceKind.EXCHANGE, 'kraken', 100),
      at(SourceKind.MANUAL, 'kraken', 5),
      at(SourceKind.MANUAL, 'external', 30),
      chain('btc', 500),
    ], { locationOfChain });

    const manual = narrowToKind(merged, SourceKind.MANUAL);

    expect(summary(manual)).toEqual([
      { key: 'external', kinds: ['manual'], value: '30' },
      { key: 'kraken', kinds: ['manual'], value: '5' },
    ]);
    expect(manual[1].target).toEqual({ location: 'kraken', type: 'manual' });
  });
});
