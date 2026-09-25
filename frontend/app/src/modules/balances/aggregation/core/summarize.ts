import type { AssetBalanceWithPriceAndChains } from '@rotki/common';
import type {
  AggregationContext,
  AssetBalanceEntries,
  SummaryOptions,
} from '@/modules/balances/aggregation/core/aggregation-types';
import { pipe } from 'plainfp';
import { groupByCollection } from '@/modules/balances/aggregation/core/collections';
import { mergeSources } from '@/modules/balances/aggregation/core/merge';
import { compareRowsByValue, holdingRow, toHolding } from '@/modules/balances/aggregation/core/rows';

function ungroupedRows(merged: AssetBalanceEntries, context: AggregationContext): AssetBalanceWithPriceAndChains[] {
  return Object.entries(merged).map(([asset, perProtocol]) => holdingRow(toHolding(asset, perProtocol, context)));
}

/**
 * One priced row per asset across the given sources, highest value first.
 *
 * @remarks
 * Adding a source means normalising it to {@link AssetBalanceEntries} (see `sources.ts`) and passing
 * it here; nothing downstream knows which source an entry came from.
 */
export function summarizeBalances(
  sources: readonly AssetBalanceEntries[],
  context: AggregationContext,
  options: SummaryOptions = {},
): AssetBalanceWithPriceAndChains[] {
  const { groupCollections = true, hideIgnored = true } = options;
  return pipe(
    mergeSources(sources, context, hideIgnored),
    merged => (groupCollections ? groupByCollection(merged, context) : ungroupedRows(merged, context)),
    rows => rows.sort(compareRowsByValue),
  );
}
