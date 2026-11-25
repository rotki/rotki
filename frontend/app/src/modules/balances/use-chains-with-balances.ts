import type { AssetProtocolBalances } from '@/modules/balances/types/blockchain-balances';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue';
import { groupAddresses } from '@/modules/accounts/core/account-groups';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { isListedAsset } from '@/modules/balances/aggregation/core/merge';
import { useAggregationContext } from '@/modules/balances/aggregation/use-aggregation-context';
import { useBalancesStore } from '@/modules/balances/use-balances-store';

/**
 * Of the given chains, the ones where an account group holds an asset or owes a liability that its
 * tables would list, in the order given.
 *
 * @remarks
 * Agrees with `useBlockchainBalances` on what is empty, through the same visible balances and
 * {@link isListedAsset}, but only asks whether anything is left, so it prices nothing. It looks up
 * the group's own addresses on the given chains only, and keeps the address set apart so a balance
 * update does not walk every account again.
 */
export function useChainsWithBalances(
  groupId: MaybeRefOrGetter<string | undefined>,
  chains: MaybeRefOrGetter<string[]>,
): ComputedRef<string[]> {
  const { visibleBalances } = storeToRefs(useBalancesStore());
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const context = useAggregationContext();

  const addresses = computed<string[]>(() => {
    const group = toValue(groupId);
    return group ? [...groupAddresses(get(accounts), group)] : [];
  });

  const listed = (assets: AssetProtocolBalances): boolean => Object.keys(assets).some(asset => isListedAsset(asset, context));

  return computed<string[]>(() => {
    const balances = get(visibleBalances);
    const owned = get(addresses);
    return toValue(chains).filter(chain => owned.some((address) => {
      const balance = balances[chain]?.[address];
      return balance !== undefined && (listed(balance.assets) || listed(balance.liabilities));
    }));
  });
}
