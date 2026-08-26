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
 * Builds the pill-bar fields for the Kraken staking page: one `period` pill over both date bounds.
 *
 * @remarks
 * Date resolution comes from `dateDeserializer`/`dateBoundParser` rather than
 * `useSharedFieldResolvers`, whose date entries are exactly those two calls: this bar has no asset,
 * location or address field, so the shared hook would pull four stores in for a single date.
 */
export function useKrakenStakingFields(): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  const dateInputFormat = useSetting('dateInputFormat');

  return [toDateFieldDef({
    formatBound: dateDeserializer(dateInputFormat),
    key: 'period',
    label: (): string => t('kraken_staking_events.filter.period'),
    lowerKey: KrakenStakingFilterValueKeys.START,
    parseBound: dateBoundParser(dateInputFormat),
    upperKey: KrakenStakingFilterValueKeys.END,
  })];
}
