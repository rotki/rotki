import type { ComputedRef } from 'vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { hasAccountAddress } from '@/utils/blockchain/accounts';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';

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
      accounts.filter(hasAccountAddress).map(account => getAccountAddress(account)),
    ]));
  });

  const getAddresses = (chain: string): string[] => get(addresses)[chain] ?? [];

  return {
    addresses,
    getAddresses,
  };
}
