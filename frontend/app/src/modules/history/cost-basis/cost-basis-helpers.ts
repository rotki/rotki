import type { BigNumber } from '@rotki/common';
import { CostBasisDirection, type CostBasisEntry, type CostBasisReceive, type CostBasisSpend } from '@/modules/history/cost-basis/types';

export const CostBasisSummaryKind = {
  ACQUISITION: 'acquisition',
  DISPOSAL: 'disposal',
  TRANSFER: 'transfer',
} as const;

export type CostBasisSummaryKind = typeof CostBasisSummaryKind[keyof typeof CostBasisSummaryKind];

/** What an event's row shows: one figure and the basis behind it, both in the user's currency. */
export interface CostBasisSummary {
  kind: CostBasisSummaryKind;
  /** The cost of what was acquired, or the basis of what was disposed of or moved. */
  basis: BigNumber;
  /** The taxable gain or loss. Set only for a disposal. */
  pnl?: BigNumber;
}

function isSpend(entry: CostBasisEntry): entry is CostBasisSpend {
  return entry.direction === CostBasisDirection.SPEND;
}

function isReceive(entry: CostBasisEntry): entry is CostBasisReceive {
  return entry.direction === CostBasisDirection.RECEIVE;
}

/**
 * Reduces the entries of an event to what its row shows.
 *
 * @remarks
 * A spend that has a receive next to it moved the asset between two of the user's own buckets,
 * which realizes nothing, so it is told apart from a disposal by that receive rather than by a
 * gain of zero, which a disposal at cost has too.
 *
 * @param entries - the cost basis entries of one event
 * @param amount - the amount of the event, which is what an acquisition's basis per unit is for
 * @returns undefined when the event has no entries
 */
export function summarizeCostBasis(entries: CostBasisEntry[], amount: BigNumber): CostBasisSummary | undefined {
  const spend = entries.find(isSpend);
  const receive = entries.find(isReceive);
  if (spend) {
    return receive
      ? { basis: spend.basisRemoved, kind: CostBasisSummaryKind.TRANSFER }
      : { basis: spend.basisRemoved, kind: CostBasisSummaryKind.DISPOSAL, pnl: spend.realizedPnl };
  }
  if (receive)
    return { basis: receive.basisPerUnit.multipliedBy(amount), kind: CostBasisSummaryKind.ACQUISITION };

  return undefined;
}
