import type { MaybeRefOrGetter, Ref, WritableComputedRef } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toHumanReadable } from '@rotki/common';
import { useBlockchainAccountOptions } from '@/modules/accounts/use-blockchain-account-options';
import { type AccountFieldOptions, toAccountField } from '@/modules/core/table/filters/shared/account-field';
import { listParam, type PillParams, stringParam, toPillParams } from '@/modules/core/table/param-refs';
import { toParamFieldDef } from '@/modules/core/table/pill/core/field-adapter';

/** The keys the airdrops table filters on. Not wire keys: the page holds every airdrop already. */
const AirdropFilterKeys = {
  ACCOUNTS: 'addresses',
  STATUS: 'status',
} as const;

/**
 * The statuses a row reads as. `all` was the select's first option and is not one of these: the
 * absence of the pill is what "all" means, the same way it does on every other bar.
 */
const airdropStatuses: readonly string[] = ['unknown', 'unclaimed', 'claimed', 'missed'];

/** Whether a raw value (a status the url can carry) names a status the page knows. */
export function isAirdropStatus(value: string): boolean {
  return airdropStatuses.includes(value);
}

/**
 * The account pill's values for the airdrops table: the tracked EVM accounts that actually have an
 * airdrop, which is what the selector this replaces offered through `usable-addresses`. Only the
 * offered list is narrowed — how an account reads is the shared resolution every account pill uses.
 */
function useAirdropAccountOptions(eligible: MaybeRefOrGetter<string[]>): AccountFieldOptions {
  const accounts = useBlockchainAccountOptions('evm');

  return {
    ...accounts,
    suggest: (): string[] => {
      const addresses = new Set(toValue(eligible));
      return accounts.suggest().filter(address => addresses.has(address));
    },
  };
}

/**
 * The pill-bar fields for the airdrops table: whose airdrops to show, and which claim state.
 *
 * Both were selectors above the table, and both are param-bound because this table has no filter
 * bag: it narrows the airdrops the page already holds rather than asking the backend.
 */
export function useAirdropFields(eligible: MaybeRefOrGetter<string[]>): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  const accounts = useAirdropAccountOptions(eligible);

  return [
    toAccountField(
      { label: (): string => t('common.account'), paramKey: AirdropFilterKeys.ACCOUNTS, to: 'both' },
      accounts,
    ),
    toParamFieldDef({
      key: 'status',
      label: (): string => t('common.status'),
      // An airdrop is in one state, so a second status would only widen back to every row.
      multiple: false,
      paramKey: AirdropFilterKeys.STATUS,
      resolveLabel: (value: string): string => toHumanReadable(value, 'sentence'),
      suggest: (): string[] => [...airdropStatuses],
      to: 'both',
    }),
  ];
}

/** The page's two refs as the bar's params bag. */
export function airdropParams(addresses: Ref<string[]>, status: Ref<string>): WritableComputedRef<PillParams> {
  return toPillParams({
    addresses: listParam(addresses),
    // A status the url invented would filter every row away and read as an empty table.
    status: stringParam(status, { admit: isAirdropStatus }),
  });
}
