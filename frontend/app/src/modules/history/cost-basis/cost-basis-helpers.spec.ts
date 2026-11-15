import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { CostBasisSummaryKind, summarizeCostBasis } from '@/modules/history/cost-basis/cost-basis-helpers';
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

  it('should report a spend with a receive next to it as a transfer with no gain', () => {
    const summary = summarizeCostBasis([spend, receive], bigNumberify('1'));
    expect(summary?.kind).toBe(CostBasisSummaryKind.TRANSFER);
    expect(summary?.basis.toString()).toBe('100');
    expect(summary?.pnl).toBeUndefined();
  });
});
