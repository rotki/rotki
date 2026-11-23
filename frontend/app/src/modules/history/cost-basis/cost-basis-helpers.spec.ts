import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { CostBasisSummaryKind, mergeCostBasisSummaries, summarizeCostBasis } from '@/modules/history/cost-basis/cost-basis-helpers';
import { CostBasisDirection, type CostBasisEntry } from '@/modules/history/cost-basis/types';

const bucket = { asset: 'ETH', location: 'ethereum', locationLabel: '0xA', method: 'fifo', protocol: null };

const spend: CostBasisEntry = {
  ...bucket,
  basisRemaining: bigNumberify('0'),
  basisRemoved: bigNumberify('100'),
  direction: CostBasisDirection.SPEND,
  lots: [],
  proceeds: bigNumberify('100'),
  realizedPnl: bigNumberify('0'),
  taxfreePnl: bigNumberify('0'),
};

const receive: CostBasisEntry = {
  ...bucket,
  basisPerUnit: bigNumberify('50'),
  basisSource: 'price_oracle',
  direction: CostBasisDirection.RECEIVE,
  lotIds: ['1'],
};

describe('summarizeCostBasis', () => {
  it('should be undefined for an event without entries', () => {
    expect(summarizeCostBasis([], bigNumberify('2'))).toBeUndefined();
  });

  it('should total an acquisition as its basis per unit for the amount received', () => {
    const summary = summarizeCostBasis([receive], bigNumberify('2'));
    expect(summary?.kind).toBe(CostBasisSummaryKind.ACQUISITION);
    expect(summary?.basis.toString()).toBe('100');
    expect(summary?.pnl).toBeUndefined();
  });

  it('should report a spend sold at cost as a disposal with a gain of zero', () => {
    const summary = summarizeCostBasis([spend], bigNumberify('1'));
    expect(summary?.kind).toBe(CostBasisSummaryKind.DISPOSAL);
    expect(summary?.basis.toString()).toBe('100');
    expect(summary?.pnl?.toString()).toBe('0');
  });

  it('should carry a tax free gain next to the taxable one, and leave out one of zero', () => {
    expect(summarizeCostBasis([spend], bigNumberify('1'))?.taxfreePnl).toBeUndefined();
    const summary = summarizeCostBasis([{ ...spend, taxfreePnl: bigNumberify('4000') }], bigNumberify('1'));
    expect(summary?.pnl?.toString()).toBe('0');
    expect(summary?.taxfreePnl?.toString()).toBe('4000');
  });

  it('should omit the gain for an unpriced disposal', () => {
    const summary = summarizeCostBasis([{ ...spend, proceeds: null, realizedPnl: null, taxfreePnl: null }], bigNumberify('1'));
    expect(summary?.kind).toBe(CostBasisSummaryKind.DISPOSAL);
    expect(summary?.basis.toString()).toBe('100');
    expect(summary?.pnl).toBeUndefined();
  });

  it('should omit the gain when a spend has no proceeds', () => {
    const summary = summarizeCostBasis([{ ...spend, proceeds: null, realizedPnl: bigNumberify('0'), taxfreePnl: null }], bigNumberify('1'));
    expect(summary?.kind).toBe(CostBasisSummaryKind.DISPOSAL);
    expect(summary?.basis.toString()).toBe('100');
    expect(summary?.pnl).toBeUndefined();
  });

  it('should report a spend with a receive next to it as a transfer with no gain', () => {
    const summary = summarizeCostBasis([spend, receive], bigNumberify('1'));
    expect(summary?.kind).toBe(CostBasisSummaryKind.TRANSFER);
    expect(summary?.basis.toString()).toBe('100');
    expect(summary?.pnl).toBeUndefined();
  });
});

describe('mergeCostBasisSummaries', () => {
  const disposal = { basis: bigNumberify('100'), kind: CostBasisSummaryKind.DISPOSAL, pnl: bigNumberify('20') };

  it('should pass a single summary through and be undefined for none', () => {
    expect(mergeCostBasisSummaries([])).toBeUndefined();
    expect(mergeCostBasisSummaries([disposal])).toBe(disposal);
  });

  it('should add up the basis, gain and tax free gain of several disposals', () => {
    const merged = mergeCostBasisSummaries([
      disposal,
      { ...disposal, basis: bigNumberify('50'), pnl: bigNumberify('-5'), taxfreePnl: bigNumberify('30') },
    ]);
    expect(merged?.kind).toBe(CostBasisSummaryKind.DISPOSAL);
    expect(merged?.basis.toString()).toBe('150');
    expect(merged?.pnl?.toString()).toBe('15');
    expect(merged?.taxfreePnl?.toString()).toBe('30');
  });

  it('should leave the gain out when one of the events is unpriced', () => {
    const merged = mergeCostBasisSummaries([disposal, { basis: bigNumberify('50'), kind: CostBasisSummaryKind.DISPOSAL }]);
    expect(merged?.basis.toString()).toBe('150');
    expect(merged?.pnl).toBeUndefined();
    expect(merged?.taxfreePnl).toBeUndefined();
  });
});
