import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef } from 'vue';
import { isAddressAccount } from '@/modules/accounts/account-utils';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';

interface UseAccountAddressesReturn {
  getAddresses: (chain: string) => string[];
  addresses: ComputedRef<Record<string, string[]>>;
}

export function useAccountAddresses(): UseAccountAddressesReturn {
  const { accounts } = storeToRefs(useBlockchainAccountsStore());

  const addresses = computed<Record<string, string[]>>(() => {
    const accountData = get(accounts);
    if (!accountData)
      return {};

    return Object.fromEntries(Object.entries(accountData).map(([chain, accounts]) => [
      chain,
      accounts.filter(isAddressAccount).map(({ address }) => address),
    ]));
  });

  const getAddresses = (chain: string): string[] => get(addresses)[chain] ?? [];

  return {
    addresses,
    getAddresses,
  };
}
