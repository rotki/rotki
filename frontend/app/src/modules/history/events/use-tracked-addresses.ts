import type { Ref } from 'vue';
import { useAccountLoadState } from '@/modules/accounts/use-account-load-state';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';

interface UseTrackedAddressesReturn {
  /** ⚠️ Only an answer once {@link accountsRead} is true. */
  isAddressTracked: (address: string | undefined | null) => boolean;
  /** The accounts have been read, so a negative {@link isAddressTracked} means untracked. */
  accountsRead: Readonly<Ref<boolean>>;
}

/**
 * Whether rotki tracks an address, across every chain: an address tracked anywhere counts as
 * tracked, so a negative answer means no decoded event for it can exist in the history at
 * all. That is what makes it the deciding question for an unmatched row - both for a bridge
 * leg and for an exchange withdrawal, whose counterpart can then only be external.
 *
 * ⚠️ The store only ever *gains* addresses, so a negative answer is worthless until the accounts
 * have been read: before that an empty store is indistinguishable from a user tracking nothing,
 * and every address on screen looks untracked. That is what {@link accountsRead} is for.
 */
export const useTrackedAddresses = createSharedComposable((): UseTrackedAddressesReturn => {
  const { addresses } = useAccountAddresses();
  const { ready } = useAccountLoadState();

  const trackedAddresses = computed<Set<string>>(() => {
    const tracked = new Set<string>();
    for (const chainAddresses of Object.values(get(addresses))) {
      for (const address of chainAddresses)
        tracked.add(address.toLowerCase());
    }
    return tracked;
  });

  function isAddressTracked(address: string | undefined | null): boolean {
    return !!address && get(trackedAddresses).has(address.toLowerCase());
  }

  return {
    accountsRead: ready,
    isAddressTracked,
  };
});
