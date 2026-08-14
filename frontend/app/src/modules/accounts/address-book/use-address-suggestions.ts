import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { Blockchain } from '@rotki/common';
import { each } from 'es-toolkit/compat';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';

interface AddressSelection {
  /** The address the form currently holds. */
  readonly selected: MaybeRefOrGetter<string>;
  /** Called when the selected address stops being offered for the chosen chain. */
  readonly clear: () => void;
}

/**
 * The addresses offered for a chain, which are the tracked ones that have no name yet.
 *
 * The list is driven by the chosen chain, so an address picked for one chain can disappear from it
 * when the chain changes. Leaving it selected would name an address the entry no longer offers, so
 * it is cleared: only when it was on the previous list, since an address the user typed themselves
 * was never offered and must survive.
 */
export function useAddressSuggestions(
  blockchain: MaybeRefOrGetter<string | null>,
  address: AddressSelection,
): ComputedRef<string[]> {
  const { addresses } = useAccountAddresses();
  const { getAddressName, useAddressesWithoutNames } = useAddressNameResolution();

  const suggestions = useAddressesWithoutNames(blockchain);

  /** Resolving every tracked address is what decides which of them are still unnamed. */
  function fetchNames(): void {
    const addressMap = get(addresses);

    each(Blockchain, (chain) => {
      addressMap[chain]?.forEach(address => getAddressName(address, chain));
    });
  }

  watch(suggestions, (suggestions, oldSuggestions) => {
    const selected = toValue(address.selected);
    if (toValue(blockchain) && oldSuggestions.includes(selected) && !suggestions.includes(selected))
      address.clear();
  });

  watchEffect(fetchNames);
  onMounted(fetchNames);

  return suggestions;
}
