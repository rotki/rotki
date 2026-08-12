import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { isNft } from '@/modules/assets/nft-utils';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { BalanceType } from '@/modules/balances/types/balances';
import { type BalanceSnapshot, ZeroValueFilter } from '@/modules/dashboard/snapshots';
import { useSnapshotAssetFilters } from '@/modules/dashboard/snapshots/composables/use-snapshot-asset-filters';
import {
  type SnapshotHiddenCounts,
  useSnapshotBalanceFields,
} from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-fields';
import { type Filters, readSnapshotFilters, SnapshotCategories, type SnapshotCategory } from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-filter';

export type IndexedBalanceSnapshot = BalanceSnapshot & { index: number; categoryLabel: string };

interface UseSnapshotBalanceRowsReturn {
  /** The pill-bar fields, built here because their labels carry the counts below. */
  fields: ComputedRef<FieldDef[]>;
  /** The rows that survive every active pill. */
  filteredData: ComputedRef<IndexedBalanceSnapshot[]>;
  /** How many rows the hide-defaults are keeping off screen, shown as a chip beside the bar. */
  hiddenCount: ComputedRef<number>;
  /** How many rows are valueless, which gates the bulk-delete action. */
  zeroValueCount: ComputedRef<number>;
}

function matchesCategory(item: IndexedBalanceSnapshot, category?: SnapshotCategory): boolean {
  switch (category) {
    case SnapshotCategories.ASSET:
      return item.category === BalanceType.ASSET && !isNft(item.assetIdentifier);
    case SnapshotCategories.LIABILITY:
      return item.category === BalanceType.LIABILITY;
    case SnapshotCategories.NFT:
      return isNft(item.assetIdentifier);
    // No category pill: every kind of row qualifies.
    case undefined:
    default:
      return true;
  }
}

function matchesZeroValue(item: IndexedBalanceSnapshot, mode: ZeroValueFilter): boolean {
  switch (mode) {
    case ZeroValueFilter.HIDE:
      return !item.usdValue.isZero();
    case ZeroValueFilter.ONLY:
      return item.usdValue.isZero();
    case ZeroValueFilter.ALL:
    default:
      return true;
  }
}

/**
 * The snapshot balance rows the table actually shows, and the fields the bar narrows them with.
 *
 * Spam, ignored and zero-value rows are hidden unless a pill says otherwise, so each of those three
 * pills reads as a departure from a default rather than as a plain value: an absent pill has to
 * mean what the unticked checkbox this replaces meant.
 */
export function useSnapshotBalanceRows(
  data: MaybeRefOrGetter<IndexedBalanceSnapshot[]>,
  filters: MaybeRefOrGetter<Filters>,
): UseSnapshotBalanceRowsReturn {
  const { getAssetField } = useAssetInfoRetrieval();
  const { isIgnoredAsset, isSpamAsset } = useSnapshotAssetFilters();

  const active = computed(() => readSnapshotFilters(toValue(filters)));

  const spamCount = computed<number>(
    () => toValue(data).filter(item => isSpamAsset(item.assetIdentifier)).length,
  );
  const ignoredCount = computed<number>(
    () => toValue(data).filter(item => isIgnoredAsset(item.assetIdentifier)).length,
  );
  const zeroValueCount = computed<number>(
    () => toValue(data).filter(item => item.usdValue.isZero()).length,
  );

  const fields = useSnapshotBalanceFields((): SnapshotHiddenCounts => ({
    ignored: get(ignoredCount),
    spam: get(spamCount),
    zeroValue: get(zeroValueCount),
  }));

  /** Lower-cased symbol/name/identifier haystack so the text filter matches what the user reads. */
  function haystack(identifier: string): string {
    const symbol = getAssetField(identifier, 'symbol');
    const name = getAssetField(identifier, 'name');
    return `${identifier} ${symbol} ${name}`.toLowerCase();
  }

  const filteredData = computed<IndexedBalanceSnapshot[]>(() => {
    const { category, search, showIgnored, showSpam, zeroValue } = get(active);
    const text = search.toLowerCase().trim();
    return toValue(data).filter(item =>
      matchesCategory(item, category)
      && (showSpam || !isSpamAsset(item.assetIdentifier))
      && (showIgnored || !isIgnoredAsset(item.assetIdentifier))
      && matchesZeroValue(item, zeroValue)
      && (!text || haystack(item.assetIdentifier).includes(text)),
    );
  });

  /**
   * Suppressed while isolating zero-value rows: there the point is what is shown, not what is
   * hidden, and the pill itself says so.
   */
  const hiddenCount = computed<number>(() => {
    const { showIgnored, showSpam, zeroValue } = get(active);
    if (zeroValue === ZeroValueFilter.ONLY)
      return 0;

    return toValue(data).filter(item =>
      (!showSpam && isSpamAsset(item.assetIdentifier))
      || (!showIgnored && isIgnoredAsset(item.assetIdentifier))
      || (zeroValue === ZeroValueFilter.HIDE && item.usdValue.isZero()),
    ).length;
  });

  return {
    fields,
    filteredData,
    hiddenCount,
    zeroValueCount,
  };
}
