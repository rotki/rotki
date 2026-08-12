import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { toNameField } from '@/modules/core/table/filters/shared/name-field';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { ZeroValueFilter } from '@/modules/dashboard/snapshots';
import {
  SnapshotBalanceFilterKeys,
  SnapshotCategories,
  zeroValueChoices,
} from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-filter';

/** How many rows each hide-filter is currently keeping off screen. */
export interface SnapshotHiddenCounts {
  readonly ignored: number;
  readonly spam: number;
  readonly zeroValue: number;
}

/**
 * The pill-bar fields for the snapshot balances table.
 *
 * Three of the five say what the table would otherwise not be showing. Spam, ignored and
 * zero-value rows are hidden by default, so each pill expresses the departure from that default and
 * an absent pill means exactly what the unticked checkbox it replaces meant. The counts ride the
 * value labels, the way they rode the checkbox labels: choosing to show ignored rows is a different
 * decision when there are none.
 *
 * Reactive because those counts are, and because a filter offering `(0)` everywhere would still be
 * offering it.
 */
export function useSnapshotBalanceFields(counts: MaybeRefOrGetter<SnapshotHiddenCounts>): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });

  const categoryLabels = computed<Map<string, string>>(() => new Map([
    [SnapshotCategories.ASSET, t('dashboard.snapshot.detail.balances.asset')],
    [SnapshotCategories.LIABILITY, t('dashboard.snapshot.detail.balances.liability')],
    [SnapshotCategories.NFT, t('dashboard.snapshot.detail.balances.nft')],
  ]));

  const zeroValueLabels = computed<Map<string, string>>(() => new Map([
    [ZeroValueFilter.ALL, t('dashboard.snapshot.detail.balances.zero_value.shown')],
    [ZeroValueFilter.ONLY, t('dashboard.snapshot.detail.balances.zero_value.only')],
  ]));

  return computed<FieldDef[]>(() => {
    const { ignored, spam, zeroValue } = toValue(counts);

    return [
      toNameField(
        SnapshotBalanceFilterKeys.SEARCH,
        (): string => t('common.asset'),
      ),
      toMatchFieldDef({
        key: SnapshotBalanceFilterKeys.CATEGORY,
        label: (): string => t('dashboard.snapshot.detail.balances.category'),
        multiple: false,
        resolveLabel: (value: string): string => get(categoryLabels).get(value) ?? value,
        suggest: (): string[] => Object.values(SnapshotCategories),
      }),
      toMatchFieldDef({
        key: SnapshotBalanceFilterKeys.SHOW_SPAM,
        label: (): string => t('dashboard.snapshot.detail.balances.show_spam', { count: spam }, spam),
        multiple: false,
        valueType: FilterValueTypes.BOOLEAN,
      }),
      toMatchFieldDef({
        key: SnapshotBalanceFilterKeys.SHOW_IGNORED,
        label: (): string => t('dashboard.snapshot.detail.balances.show_ignored', { count: ignored }, ignored),
        multiple: false,
        valueType: FilterValueTypes.BOOLEAN,
      }),
      toMatchFieldDef({
        key: SnapshotBalanceFilterKeys.ZERO_VALUE,
        label: (): string => t('dashboard.snapshot.detail.balances.zero_value.label', { count: zeroValue }, zeroValue),
        multiple: false,
        resolveLabel: (value: string): string => get(zeroValueLabels).get(value) ?? value,
        suggest: (): string[] => zeroValueChoices,
      }),
    ];
  });
}
