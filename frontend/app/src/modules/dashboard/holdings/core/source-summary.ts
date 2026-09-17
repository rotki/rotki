import type { BigNumber } from '@rotki/common';
import { pipe } from 'plainfp';
import { filter, map } from 'plainfp/arrays';
import { bigNumberSum } from '@/modules/core/common/data/calculation';
import {
  ExtraKind,
  type HoldingsSummary,
  SOURCE_KIND_ORDER,
  type SourceContribution,
  type SourceKind,
  type SourceTotal,
  type SummaryKind,
} from './holdings-types';

interface SummaryExtras {
  /** NFT value in the main currency, or `undefined` when NFTs do not count toward net worth. */
  readonly nfts: BigNumber | undefined;
  readonly liabilities: BigNumber;
}

/**
 * Totals each source kind, in the order the dashboard lists them.
 *
 * @remarks
 * Shares are of gross assets, not of net worth, so they add up to 100% and never pass it however
 * large the liabilities are. Kinds holding nothing are left out of `sources` and listed in
 * `emptyKinds` instead, unless they are still being priced: a chain whose prices have not
 * arrived sums to zero, and dropping it would read as the user holding nothing there.
 */
export function summarizeSources(contributions: readonly SourceContribution[], { liabilities, nfts }: SummaryExtras): HoldingsSummary {
  const ofKind = (kind: SourceKind): SourceContribution[] => contributions.filter(contribution => contribution.kind === kind);

  const kindTotals: { kind: SummaryKind; value: BigNumber; loading: boolean }[] = [
    ...SOURCE_KIND_ORDER.map(kind => ({
      kind,
      loading: ofKind(kind).some(contribution => contribution.loading),
      value: bigNumberSum(ofKind(kind).map(contribution => contribution.value)),
    })),
    ...(nfts ? [{ kind: ExtraKind.NFT, loading: false, value: nfts }] : []),
  ];
  const gross = bigNumberSum(kindTotals.map(({ value }) => value));

  return {
    emptyKinds: SOURCE_KIND_ORDER.filter(kind => ofKind(kind).length === 0),
    gross,
    liabilities,
    loading: kindTotals.some(({ loading }) => loading),
    sources: pipe(
      kindTotals,
      filter(({ loading, value }) => loading || !value.isZero()),
      map(({ kind, loading, value }): SourceTotal => ({ kind, loading, share: gross.isZero() ? gross : value.div(gross), value })),
    ),
  };
}

/** Segment weights for the source bar; equal when the user hides shares, so sizes reveal nothing. */
export function barWeights(sources: readonly SourceTotal[], showShares: boolean): number[] {
  return sources.map(source => (showShares ? source.share.toNumber() : 1));
}
