import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { type AssetBalance, getTextToken } from '@rotki/common';
import { useAssetSelectInfo } from '@/modules/assets/use-asset-select-info';
import { type AssetSearchTokens, assetSearchTokens, assetTokensExactlyMatch, assetTokensMatch } from '@/modules/core/common/display/assets';

interface UseAssetBalanceSearchReturn<T extends AssetBalance> {
  matches: ComputedRef<T[]>;
  prioritizeExactMatches: (rows: T[]) => T[];
}

/**
 * Searching a balance list by asset name, symbol or contract address.
 *
 * The rows a table renders are resolved through the asset info cache, but a search reads the
 * metadata of *every* balance, including the ones on pages nobody has looked at. Those are never
 * resolved by rendering, so the list is prefetched here as soon as it arrives: without it the
 * first search runs against nothing and reports no results until its own request returns.
 *
 * The tokens are indexed per asset rather than rebuilt per keystroke. The index depends on the
 * balances and on the resolved metadata, so it is rebuilt when either changes and typing costs
 * only the string compares themselves.
 */
export function useAssetBalanceSearch<T extends AssetBalance>(
  balances: MaybeRefOrGetter<T[]>,
  search: MaybeRefOrGetter<string>,
): UseAssetBalanceSearchReturn<T> {
  const { getAssetInfo, prefetchAssetInfo } = useAssetSelectInfo();

  watchImmediate(() => toValue(balances), (items) => {
    prefetchAssetInfo(items.map(item => item.asset));
  });

  const index = computed<Map<string, AssetSearchTokens>>(() => {
    const tokens = new Map<string, AssetSearchTokens>();
    for (const { asset } of toValue(balances)) {
      if (!tokens.has(asset))
        tokens.set(asset, assetSearchTokens(asset, getAssetInfo(asset)));
    }
    return tokens;
  });

  const keyword = computed<string>(() => getTextToken(toValue(search)));

  const matches = computed<T[]>(() => {
    const term = get(keyword);
    const rows = toValue(balances);
    if (!term)
      return rows;

    const tokens = get(index);
    return rows.filter(row => assetTokensMatch(tokens.get(row.asset), term));
  });

  /**
   * Moves rows whose whole symbol or name is what was typed to the front, leaving the rest in the
   * order the table's own column sort put them.
   *
   * Applied after sorting, because the column sort is what the header's arrow promises. Only an
   * exact match jumps it, which reads as "what I typed is first" rather than as the table ignoring
   * the column you sorted by.
   */
  function prioritizeExactMatches(rows: T[]): T[] {
    const term = get(keyword);
    if (!term)
      return rows;

    const tokens = get(index);
    const exact: T[] = [];
    const rest: T[] = [];
    for (const row of rows) {
      if (assetTokensExactlyMatch(tokens.get(row.asset), term))
        exact.push(row);
      else
        rest.push(row);
    }

    return exact.length > 0 ? [...exact, ...rest] : rows;
  }

  return {
    matches,
    prioritizeExactMatches,
  };
}
