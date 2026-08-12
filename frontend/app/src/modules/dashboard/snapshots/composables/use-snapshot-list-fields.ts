import type { WritableComputedRef } from 'vue';
import type { WritableRef } from '@/modules/core/common/common-types';
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { SnapshotListFilters } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import { assert } from '@rotki/common';
import { dateBoundParser, dateDeserializer } from '@/modules/core/common/data/date';
import { toDateFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { useSetting } from '@/modules/settings/use-setting';

/** The keys the two bounds are stored under, matching `SnapshotListFilters`. */
export const SnapshotListFilterKeys = {
  END: 'toTimestamp',
  START: 'fromTimestamp',
} as const;

/**
 * The pill-bar field for the snapshot list: one `period` pill in place of the two date pickers the
 * page carried beside its table.
 *
 * Date resolution comes from `dateDeserializer`/`dateBoundParser` rather than
 * `useSharedFieldResolvers`, whose date entries are exactly these two calls: this bar has no asset,
 * location or address field, so going through the shared hook would pull those stores in for a
 * single date. Same reasoning as the Kraken staking bar.
 */
export function useSnapshotListFields(): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  const dateInputFormat = useSetting('dateInputFormat');

  // The bounds are stored as the unix seconds the list filters on, so no serializer.
  return [toDateFieldDef({
    formatBound: dateDeserializer(dateInputFormat),
    key: 'period',
    label: (): string => t('dashboard.snapshot.list.range.period'),
    lowerKey: SnapshotListFilterKeys.START,
    parseBound: dateBoundParser(dateInputFormat),
    upperKey: SnapshotListFilterKeys.END,
  })];
}

/**
 * Bridges the list's `{ fromTimestamp, toTimestamp }` filters to the flat keyword map the bar
 * speaks. The page keeps the object form because that is what the list filters on and what it
 * mirrors into the URL query.
 */
export function toSnapshotListMatches(
  filters: WritableRef<SnapshotListFilters>,
): WritableComputedRef<MatchedKeywordWithBehaviour<string>> {
  return computed<MatchedKeywordWithBehaviour<string>>({
    get() {
      const { fromTimestamp, toTimestamp } = get(filters);
      return {
        ...(fromTimestamp ? { [SnapshotListFilterKeys.START]: fromTimestamp.toString() } : {}),
        ...(toTimestamp ? { [SnapshotListFilterKeys.END]: toTimestamp.toString() } : {}),
      };
    },
    set(value) {
      const from = value[SnapshotListFilterKeys.START];
      const to = value[SnapshotListFilterKeys.END];
      assert(typeof from === 'string' || from === undefined);
      assert(typeof to === 'string' || to === undefined);

      set(filters, {
        fromTimestamp: from ? Number(from) : undefined,
        toTimestamp: to ? Number(to) : undefined,
      });
    },
  });
}
