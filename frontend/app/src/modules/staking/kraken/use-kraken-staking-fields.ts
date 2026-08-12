import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { dateBoundParser, dateDeserializer } from '@/modules/core/common/data/date';
import { toDateFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { useSetting } from '@/modules/settings/use-setting';

/** The wire keys the two date bounds are stored and sent under. */
export const KrakenStakingFilterValueKeys = {
  END: 'toTimestamp',
  START: 'fromTimestamp',
} as const;

/**
 * The pill-bar fields for the Kraken staking page: one `period` pill collapsing what used to be a
 * separate start-date and end-date matcher, the way every other date pill in the app works.
 *
 * Date resolution comes from `dateDeserializer`/`dateBoundParser` rather than
 * `useSharedFieldResolvers`, whose date entries are exactly these two calls: this bar has no asset,
 * location or address field, so going through the shared hook would pull the asset, location, chain
 * and counterparty stores in for a single date.
 */
export function useKrakenStakingFields(): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  const dateInputFormat = useSetting('dateInputFormat');

  // No serializer of its own: the bounds are stored as the unix seconds they are sent as, and the
  // date editor reads and writes them through `formatBound`/`parseBound`. The old matchers' date
  // serializers belonged to the old bar, where the user typed a formatted date.
  return [toDateFieldDef({
    formatBound: dateDeserializer(dateInputFormat),
    key: 'period',
    label: (): string => t('kraken_staking_events.filter.period'),
    lowerKey: KrakenStakingFilterValueKeys.START,
    parseBound: dateBoundParser(dateInputFormat),
    upperKey: KrakenStakingFilterValueKeys.END,
  })];
}
