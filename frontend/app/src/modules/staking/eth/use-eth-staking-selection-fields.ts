import type { ComputedRef } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { Blockchain } from '@rotki/common';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { useBlockchainAccountOptions } from '@/modules/accounts/use-blockchain-account-options';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { type AccountFieldOptions, toFilterAccountField } from '@/modules/core/table/filters/shared/account-field';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { useScramble } from '@/modules/settings/use-scramble';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';

/**
 * The two ways of naming *whose* staking to show. They are one axis, not two filters: the page
 * model is a union of a validator list and an address list, so each excludes the other.
 */
export const EthStakingSelectionKeys = {
  VALIDATOR: 'validator',
  WITHDRAWAL_ADDRESS: 'withdrawalAddress',
} as const;

/**
 * The withdrawal-address pill's values: the addresses tracked on ethereum, which is what the
 * account selector this replaces offered (`:chains="[Blockchain.ETH]"`). Only the offered list is
 * narrowed; how an account reads is the shared resolution every account pill uses.
 */
function useWithdrawalAddressOptions(): AccountFieldOptions {
  const accounts = useBlockchainAccountOptions('evm');
  const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());

  return {
    ...accounts,
    suggest: (): string[] => {
      const tracked = new Set((get(accountsPerChain)[Blockchain.ETH] ?? []).map(account => getAccountAddress(account)));
      return accounts.suggest().filter(address => tracked.has(address));
    },
  };
}

/**
 * The pill-bar fields for who the staking view is showing: a validator, or the address that
 * withdrew for it.
 *
 * These used to be a `RuiButtonGroup` toggle deciding which of two inputs was rendered. The toggle
 * existed only to say the two cannot both apply, which is what `excludes` says here, declared on
 * both sides as the bar requires.
 */
export function useEthStakingSelectionFields(): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());
  const { scrambleAddress, scrambleIdentifier } = useScramble();
  const withdrawalAddresses = useWithdrawalAddressOptions();

  /** Index -> the validator it names, for the label and caption. */
  const byIndex = computed<Map<string, { publicKey: string }>>(() => new Map(
    get(ethStakingValidators).map(validator => [validator.index.toString(), { publicKey: validator.publicKey }]),
  ));

  const validatorField: FieldDef = toMatchFieldDef({
    // The key tells two indices apart while picking; on the pill the index already names the
    // validator, and a key beside it pushes every other pill off the bar.
    captionScope: 'list',
    excludes: [EthStakingSelectionKeys.WITHDRAWAL_ADDRESS],
    key: EthStakingSelectionKeys.VALIDATOR,
    label: (): string => t('eth2_page.filter.validator'),
    multiple: true,
    // Shortened the way an account's address is: a whole public key is 66 characters and crowds
    // the index it is meant to annotate off its own row.
    resolveCaption: (value: string): string | undefined => {
      const publicKey = get(byIndex).get(value)?.publicKey;
      return publicKey ? truncateAddress(scrambleAddress(publicKey), 4) : undefined;
    },
    // Matched on the raw index and key, not the shown ones: what the user types is the real value,
    // and lowercased because the search box lowercases what is typed.
    resolveKeywords: (value: string): string | undefined => {
      const publicKey = get(byIndex).get(value)?.publicKey;
      return `${value} ${publicKey ?? ''}`.toLowerCase();
    },
    // The value stays the real index, which is what the request carries; only its display follows
    // privacy mode, exactly as an address does.
    resolveLabel: (value: string): string => scrambleIdentifier(value),
    suggest: (): string[] => get(ethStakingValidators).map(validator => validator.index.toString()),
  });

  const withdrawalAddressField: FieldDef = toFilterAccountField({
    excludes: [EthStakingSelectionKeys.VALIDATOR],
    key: EthStakingSelectionKeys.WITHDRAWAL_ADDRESS,
    label: (): string => t('eth2_page.filter.withdrawal_address'),
  }, withdrawalAddresses);

  return computed<FieldDef[]>(() => [validatorField, withdrawalAddressField]);
}
