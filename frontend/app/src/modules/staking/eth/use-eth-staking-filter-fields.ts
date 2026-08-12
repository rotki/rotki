import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toHumanReadable } from '@rotki/common';
import { dateBoundParser, dateDeserializer } from '@/modules/core/common/data/date';
import { FilterOps, FilterValueTypes } from '@/modules/core/table/filtering';
import { toDateFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { useSetting } from '@/modules/settings/use-setting';
import { validStatuses } from '@/modules/staking/eth/use-eth-validator-filter';

/** The wire keys the combined filter is stored and sent under. */
export const EthStakingFilterValueKeys = {
  END: 'toTimestamp',
  START: 'fromTimestamp',
  STATUS: 'status',
} as const;

/**
 * `all` is the absence of a status filter, not a value to send: the pill is simply not there.
 * Offering it would give the user two ways to say the same thing, one of which reads as a filter.
 */
const selectableStatuses = validStatuses.filter(status => status !== 'all');

/**
 * The pill-bar fields for the eth staking page: the two date matchers collapsed into one `period`
 * pill, and the validator status.
 *
 * The one field list here that is genuinely reactive rather than only locale-dependent: which
 * fields exist turns on `disableStatus`, so this keeps a computed where the other tables no longer
 * need one.
 *
 * @param disableStatus when validators are picked by hand, a status filter cannot narrow anything
 * further, so the field is not offered at all.
 */
export function useEthStakingFilterFields(
  disableStatus: MaybeRefOrGetter<boolean>,
): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  const dateInputFormat = useSetting('dateInputFormat');

  // No serializer of its own: the bounds are stored as the unix seconds they are sent as, and the
  // date editor reads and writes them through `formatBound`/`parseBound`.
  const periodField: FieldDef = toDateFieldDef({
    formatBound: dateDeserializer(dateInputFormat),
    key: 'period',
    label: (): string => t('common.filter.period'),
    lowerKey: EthStakingFilterValueKeys.START,
    parseBound: dateBoundParser(dateInputFormat),
    upperKey: EthStakingFilterValueKeys.END,
  });

  // Declared rather than derived from a matcher: a matcher describes a field to the old text bar,
  // and this one only ever feeds the pill bar.
  const statusField: FieldDef = {
    allowExclusion: false,
    binding: { kind: 'filter' },
    key: EthStakingFilterValueKeys.STATUS,
    // `eth_validator_combined_filter.status` is the long "filter by the status of the validator"
    // hint the old bar showed; a pill wants the noun.
    label: (): string => t('common.status'),
    multiple: false,
    operators: [FilterOps.IS],
    resolveLabel: (value: string): string => toHumanReadable(value, 'sentence'),
    suggest: (): string[] => [...selectableStatuses],
    valueType: FilterValueTypes.ENUM,
  };

  return computed<FieldDef[]>(() => (
    toValue(disableStatus) ? [periodField] : [periodField, statusField]
  ));
}
