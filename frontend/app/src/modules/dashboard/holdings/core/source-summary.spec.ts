import { bigNumberify, Zero } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { type HoldingsSummary, type SourceContribution, SourceKind } from './holdings-types';
import { barWeights, summarizeSources } from './source-summary';

const contributions: SourceContribution[] = [
  { chain: 'eth', kind: SourceKind.BLOCKCHAIN, loading: false, value: bigNumberify(300) },
  { chain: 'btc', kind: SourceKind.BLOCKCHAIN, loading: false, value: bigNumberify(100) },
  { kind: SourceKind.MANUAL, loading: false, location: 'external', value: bigNumberify(50) },
  { kind: SourceKind.EXCHANGE, loading: false, location: 'kraken', value: bigNumberify(50) },
];

function totals(summary: HoldingsSummary): { kind: string; share: string; value: string }[] {
  return summary.sources.map(source => ({ kind: source.kind, share: source.share.toFixed(2), value: source.value.toFixed() }));
}

describe('summarizeSources', () => {
  it('should total each kind in the fixed order with shares of gross assets', () => {
    const summary = summarizeSources(contributions, { liabilities: Zero, nfts: undefined });

    expect(totals(summary)).toEqual([
      { kind: 'blockchain', share: '0.80', value: '400' },
      { kind: 'exchange', share: '0.10', value: '50' },
      { kind: 'manual', share: '0.10', value: '50' },
    ]);
    expect(summary.gross.toFixed()).toBe('500');
  });

  it('should list the kinds with no contributions as empty', () => {
    expect(summarizeSources(contributions, { liabilities: Zero, nfts: undefined }).emptyKinds).toEqual(['bank']);
  });

  it('should count NFTs last and in the shares only when they are passed', () => {
    const summary = summarizeSources(contributions, { liabilities: Zero, nfts: bigNumberify(500) });

    expect(totals(summary).at(-1)).toEqual({ kind: 'nft', share: '0.50', value: '500' });
    expect(summary.gross.toFixed()).toBe('1000');
  });

  it('should keep shares of gross assets when liabilities exceed them', () => {
    const summary = summarizeSources(contributions, { liabilities: bigNumberify(2000), nfts: undefined });

    expect(summary.sources[0].share.toFixed(2)).toBe('0.80');
    expect(summary.liabilities.toFixed()).toBe('2000');
  });

  it('should report no sources and no division by zero when nothing is held', () => {
    const summary = summarizeSources([], { liabilities: Zero, nfts: undefined });

    expect(summary.sources).toEqual([]);
    expect(summary.emptyKinds).toEqual(['blockchain', 'exchange', 'bank', 'manual']);
  });

  it('should leave out a kind whose contributions add up to zero', () => {
    const summary = summarizeSources([
      ...contributions,
      { kind: SourceKind.BANK, loading: false, location: 'qonto', value: Zero },
    ], { liabilities: Zero, nfts: undefined });

    expect(summary.sources.map(source => source.kind)).not.toContain('bank');
    expect(summary.emptyKinds).toEqual([]);
  });

  it('should keep a kind still being priced, marked loading, even while it sums to zero', () => {
    const summary = summarizeSources([
      { chain: 'btc', kind: SourceKind.BLOCKCHAIN, loading: true, value: Zero },
      { kind: SourceKind.MANUAL, loading: false, location: 'external', value: bigNumberify(50) },
    ], { liabilities: Zero, nfts: undefined });

    expect(summary.sources.map(({ kind, loading }) => ({ kind, loading }))).toEqual([
      { kind: 'blockchain', loading: true },
      { kind: 'manual', loading: false },
    ]);
    expect(summary.loading).toBe(true);
  });

  it('should mark a kind loading when any one of its contributions is', () => {
    const summary = summarizeSources([
      ...contributions,
      { chain: 'optimism', kind: SourceKind.BLOCKCHAIN, loading: true, value: bigNumberify(10) },
    ], { liabilities: Zero, nfts: undefined });

    expect(summary.sources.find(source => source.kind === SourceKind.BLOCKCHAIN)?.loading).toBe(true);
    expect(summary.sources.find(source => source.kind === SourceKind.MANUAL)?.loading).toBe(false);
  });

  it('should not be loading once every contribution is priced', () => {
    expect(summarizeSources(contributions, { liabilities: Zero, nfts: undefined }).loading).toBe(false);
  });
});

describe('barWeights', () => {
  const { sources } = summarizeSources(contributions, { liabilities: Zero, nfts: undefined });

  it('should weight segments by share', () => {
    expect(barWeights(sources, true)).toEqual([0.8, 0.1, 0.1]);
  });

  it('should weight segments equally when shares are hidden', () => {
    expect(barWeights(sources, false)).toEqual([1, 1, 1]);
  });
});
