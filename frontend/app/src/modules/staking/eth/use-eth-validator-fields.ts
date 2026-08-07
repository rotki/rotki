import type { ComputedRef } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toHumanReadable } from '@rotki/common';
import { FilterOps, FilterValueTypes } from '@/modules/core/table/filtering';
import { validStatuses } from '@/modules/core/table/filters/use-eth-validator-filter';

/** The wire keys the validators table filters on. */
const EthValidatorFieldKeys = {
  INDEX: 'index',
  PUBLIC_KEY: 'publicKey',
  STATUS: 'status',
} as const;

/** `all` is the absence of the pill rather than a value to send. */
const selectableStatuses = validStatuses.filter(status => status !== 'all');

/**
 * The pill-bar fields for the eth validators table.
 *
 * Declared directly rather than derived from matchers: a matcher exists to describe a field to the
 * old text bar, and this table only feeds the pill bar now. Built inside a computed so the labels
 * track the locale.
 */
export function useEthValidatorFields(): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });

  return computed<FieldDef[]>(() => [
    {
      allowExclusion: false,
      binding: { kind: 'matcher' },
      // Typed, not picked: a validator index is a number the user knows, and there is no list of
      // every index worth offering.
      freeText: true,
      key: EthValidatorFieldKeys.INDEX,
      label: t('common.validator_index'),
      multiple: true,
      operators: [FilterOps.IS],
      validate: (value: string): boolean => /^\d+$/.test(value.trim()),
      valueType: FilterValueTypes.ENUM,
    },
    {
      allowExclusion: false,
      binding: { kind: 'matcher' },
      freeText: true,
      key: EthValidatorFieldKeys.PUBLIC_KEY,
      label: t('eth2_input.public_key'),
      multiple: true,
      operators: [FilterOps.IS],
      // A BLS public key: 48 bytes of hex. Refusing anything else keeps a half-pasted key from
      // being sent as a filter.
      validate: (value: string): boolean => /^0x[\dA-Fa-f]{96}$/.test(value.trim()),
      valueType: FilterValueTypes.ENUM,
    },
    {
      allowExclusion: false,
      binding: { kind: 'matcher' },
      key: EthValidatorFieldKeys.STATUS,
      label: t('common.status'),
      multiple: true,
      operators: [FilterOps.IS],
      resolveLabel: (value: string): string => toHumanReadable(value, 'sentence'),
      suggest: (): string[] => [...selectableStatuses],
      valueType: FilterValueTypes.ENUM,
    },
  ]);
}
