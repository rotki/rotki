import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { BalanceSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import type { IndexedBalanceSnapshot } from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-rows';
import { isNft } from '@/modules/assets/nft-utils';
import { BalanceType } from '@/modules/balances/types/balances';
import { getTotalValue } from '@/modules/dashboard/snapshots/utils/snapshot-totals';
import { getSnapshotWarnings, type SnapshotWarning } from '@/modules/dashboard/snapshots/utils/snapshot-warnings';

interface UseSnapshotBalanceDisplayReturn {
  /** The snapshot's balances, indexed so an edit can name the row it came from. */
  data: ComputedRef<IndexedBalanceSnapshot[]>;
  /** Maps a row index to the sanity warnings drawn on it. */
  warningsByIndex: ComputedRef<Map<number, SnapshotWarning[]>>;
  /** The snapshot's net worth, which the share column is a fraction of. */
  total: ComputedRef<BigNumber>;
  describeWarning: (warning: SnapshotWarning) => string;
  sharePercent: (item: IndexedBalanceSnapshot) => string;
  categoryChipColor: (item: IndexedBalanceSnapshot) => 'error' | 'info' | 'grey';
  /** A liability is drawn in the error colour wherever its value appears. */
  isLiability: (item: IndexedBalanceSnapshot) => boolean;
  /** An nft row is drawn by a different component than a plain asset. */
  isNftRow: (item: IndexedBalanceSnapshot) => boolean;
}

function isLiability(item: IndexedBalanceSnapshot): boolean {
  return item.category === BalanceType.LIABILITY;
}

/**
 * How a snapshot's balance rows read: their indexed shape, the sanity flags drawn on them, and the
 * share of net worth each one accounts for.
 */
export function useSnapshotBalanceDisplay(
  snapshot: MaybeRefOrGetter<Snapshot>,
): UseSnapshotBalanceDisplayReturn {
  const { t } = useI18n({ useScope: 'global' });

  const data = computed<IndexedBalanceSnapshot[]>(() =>
    toValue(snapshot).balancesSnapshot.map((item: BalanceSnapshot, index: number) => ({
      ...item,
      categoryLabel: isNft(item.assetIdentifier)
        ? `${item.category} (${t('dashboard.snapshot.detail.balances.nft')})`
        : item.category,
      index,
    })),
  );

  /**
   * Zero-value rows are excluded: they are overwhelmingly valueless spam tokens, so flagging each
   * one floods the table. The summary surfaces their count instead.
   */
  const warningsByIndex = computed<Map<number, SnapshotWarning[]>>(() => {
    const map = new Map<number, SnapshotWarning[]>();
    for (const warning of getSnapshotWarnings(toValue(snapshot))) {
      if (warning.balanceIndex === undefined || warning.code === 'zero-value')
        continue;
      const list = map.get(warning.balanceIndex) ?? [];
      list.push(warning);
      map.set(warning.balanceIndex, list);
    }
    return map;
  });

  const total = computed<BigNumber>(() => getTotalValue(toValue(snapshot).locationDataSnapshot));

  /** Short, asset-agnostic reason for a row's sanity flag, shown in its tooltip. */
  function describeWarning(warning: SnapshotWarning): string {
    switch (warning.code) {
      case 'negative-balance':
        return t('dashboard.snapshot.detail.balances.flag_reasons.negative');
      case 'duplicate-asset':
        return t('dashboard.snapshot.detail.balances.flag_reasons.duplicate');
      case 'nft-amount':
        return t('dashboard.snapshot.detail.balances.flag_reasons.nft_amount');
      // The remaining codes are snapshot-level, not row-level, so no row carries them.
      case 'zero-value':
      case 'net-worth-swing':
      default:
        return t('dashboard.snapshot.detail.balances.flagged');
    }
  }

  /**
   * Signed share of net worth: assets contribute positively, liabilities negatively (net worth =
   * assets minus liabilities). Empty when net worth is not positive, where the ratio would be
   * meaningless.
   *
   * Compared against zero rather than through `isPositive()`, which is true *of* zero: a snapshot
   * totalling zero would otherwise divide by it and render every row's share as `Infinity`. A
   * snapshot of nothing but valueless rows is exactly that, and is what the zero-value pill
   * isolates.
   */
  function sharePercent(item: IndexedBalanceSnapshot): string {
    const net = get(total);
    if (!net.isGreaterThan(0))
      return '';
    const contribution = isLiability(item) ? item.usdValue.negated() : item.usdValue;
    return contribution.dividedBy(net).multipliedBy(100).toFormat(2);
  }

  function categoryChipColor(item: IndexedBalanceSnapshot): 'error' | 'info' | 'grey' {
    if (isLiability(item))
      return 'error';
    if (isNft(item.assetIdentifier))
      return 'info';
    return 'grey';
  }

  return {
    categoryChipColor,
    data,
    describeWarning,
    isLiability,
    isNftRow: (item: IndexedBalanceSnapshot): boolean => isNft(item.assetIdentifier),
    sharePercent,
    total,
    warningsByIndex,
  };
}
