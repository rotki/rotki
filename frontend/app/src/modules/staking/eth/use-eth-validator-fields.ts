import type { ComputedRef } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toHumanReadable } from '@rotki/common';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { EthValidatorFilterKeys, validStatuses } from '@/modules/staking/eth/use-eth-validator-filter';

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
    toMatchFieldDef({
      // Typed, not picked: a validator index is a number the user knows, and there is no list of
      // every index worth offering.
      freeText: true,
      key: EthValidatorFilterKeys.INDEX,
      label: t('common.validator_index'),
      multiple: true,
      validate: (value: string): boolean => /^\d+$/.test(value.trim()),
    }),
    toMatchFieldDef({
      freeText: true,
      key: EthValidatorFilterKeys.PUBLIC_KEY,
      label: t('eth2_input.public_key'),
      multiple: true,
      // A BLS public key: 48 bytes of hex. Refusing anything else keeps a half-pasted key from
      // being sent as a filter.
      validate: (value: string): boolean => /^0x[\dA-Fa-f]{96}$/.test(value.trim()),
    }),
    toMatchFieldDef({
      key: EthValidatorFilterKeys.STATUS,
      label: t('common.status'),
      multiple: true,
      resolveLabel: (value: string): string => toHumanReadable(value, 'sentence'),
      suggest: (): string[] => [...selectableStatuses],
    }),
  ]);
}
