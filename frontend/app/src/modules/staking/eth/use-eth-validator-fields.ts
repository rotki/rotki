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
 * old text bar, and this table only feeds the pill bar now.
 */
/**
 * Whether a value is a whole BLS public key, being 48 bytes of hex.
 *
 * @remarks
 * Both this and the index are typed rather than picked, since an index is a number the user knows
 * and neither has a list worth offering. Validating instead keeps a half-pasted key from being sent
 * as a filter.
 */
function isBlsPublicKey(value: string): boolean {
  return /^0x[\dA-Fa-f]{96}$/.test(value.trim());
}

export function useEthValidatorFields(): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });

  return [
    toMatchFieldDef({
      freeText: true,
      key: EthValidatorFilterKeys.INDEX,
      label: (): string => t('common.validator_index'),
      multiple: true,
      validate: (value: string): boolean => /^\d+$/.test(value.trim()),
    }),
    toMatchFieldDef({
      freeText: true,
      key: EthValidatorFilterKeys.PUBLIC_KEY,
      label: (): string => t('eth2_input.public_key'),
      multiple: true,
      validate: isBlsPublicKey,
    }),
    toMatchFieldDef({
      key: EthValidatorFilterKeys.STATUS,
      label: (): string => t('common.status'),
      multiple: true,
      resolveLabel: (value: string): string => toHumanReadable(value, 'sentence'),
      suggest: (): string[] => [...selectableStatuses],
    }),
  ];
}
