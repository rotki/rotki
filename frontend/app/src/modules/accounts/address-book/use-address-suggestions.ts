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
 * @remarks
 * The list is driven by the chosen chain, so a selected address can drop off it when the chain
 * changes, and keeping it would name an address the entry does not offer. It is cleared only when
 * it came from the previous list: an address the user typed themselves was never offered, and has
 * to survive.
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
