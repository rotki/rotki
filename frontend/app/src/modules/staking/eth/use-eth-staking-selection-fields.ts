import type { ComputedRef } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { Blockchain } from '@rotki/common';
import { getAccountAddress, isValidatorAccount } from '@/modules/accounts/account-utils';
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
 * account selector this replaces offered (`:chains="[Blockchain.ETH]"`), plus the addresses the
 * validators themselves withdraw to. Only the offered list is narrowed; how an account reads is the
 * shared resolution every account pill uses.
 *
 * The second half is the point: a validator's withdrawal address is named by the validator, not by
 * the account list, and tracking it as an ethereum account too is a separate decision. Offering
 * only tracked accounts meant that typing the address a validator actually withdraws to found
 * nothing, on the one filter whose whole subject is that address.
 */
function useWithdrawalAddressOptions(): AccountFieldOptions {
  const accounts = useBlockchainAccountOptions('evm');
  const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());

  const declared = computed<string[]>(() => {
    const addresses = new Set<string>();
    for (const account of get(accountsPerChain)[Blockchain.ETH2] ?? []) {
      if (isValidatorAccount(account) && account.data.withdrawalAddress)
        addresses.add(account.data.withdrawalAddress);
    }
    return [...addresses];
  });

  return {
    ...accounts,
    resolveKeywords: (address: string): string | undefined =>
      accounts.resolveKeywords(address) ?? address.toLowerCase(),
    suggest: (): string[] => {
      const tracked = new Set((get(accountsPerChain)[Blockchain.ETH] ?? []).map(account => getAccountAddress(account)));
      return [...new Set([
        ...accounts.suggest().filter(address => tracked.has(address)),
        ...get(declared),
      ])];
    },
  };
}

/**
 * Builds the pill-bar fields for who the staking view is showing: a validator, or the address that
 * withdrew for it.
 *
 * @remarks
 * The two cannot both apply, which `excludes` states. The bar requires it declared on both sides.
 */
export function useEthStakingSelectionFields(): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());
  const { scrambleAddress, scrambleIdentifier } = useScramble();
  const withdrawalAddresses = useWithdrawalAddressOptions();

  /** Maps a validator index to the validator it names, for the label and caption. */
  const byIndex = computed<Map<string, { publicKey: string }>>(() => new Map(
    get(ethStakingValidators).map(validator => [validator.index.toString(), { publicKey: validator.publicKey }]),
  ));

  /**
   * Picks validators by index, captioned with their public key.
   *
   * @remarks
   * The caption is scoped to the list: while picking, the key is what tells two indices apart, but
   * on a pill the index already names the validator and a key beside it pushes every other pill off
   * the bar. It is truncated the way an account's address is, since a whole public key crowds the
   * index it annotates off its own row.
   *
   * Keywords match the raw index and key rather than the shown ones, because what the user types is
   * the real value, lowercased to meet the search box. The value likewise stays the real index,
   * which is what the request carries; only its display follows privacy mode, exactly as an address
   * does.
   */
  const validatorField: FieldDef = toMatchFieldDef({
    captionScope: 'list',
    excludes: [EthStakingSelectionKeys.WITHDRAWAL_ADDRESS],
    key: EthStakingSelectionKeys.VALIDATOR,
    label: (): string => t('eth2_page.filter.validator'),
    multiple: true,
    resolveCaption: (value: string): string | undefined => {
      const publicKey = get(byIndex).get(value)?.publicKey;
      return publicKey ? truncateAddress(scrambleAddress(publicKey), 4) : undefined;
    },
    resolveKeywords: (value: string): string | undefined => {
      const publicKey = get(byIndex).get(value)?.publicKey;
      return `${value} ${publicKey ?? ''}`.toLowerCase();
    },
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
