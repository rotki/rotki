import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { AccountFieldOptions } from '@/modules/core/table/filters/shared/account-field';
import { getAccountAddress, getAccountLabel, getChain, isXpubAccount } from '@/modules/accounts/account-utils';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useScramble } from '@/modules/settings/use-scramble';

/** One tracked account of the shown category, as the account pill needs to read it. */
interface AccountOption {
  readonly address: string;
  /** Its tracked/ENS name, absent when it has none. */
  readonly name?: string;
  readonly tags: string[];
}

/**
 * The account pill's values for the blockchain balances table: the tracked accounts of the
 * category being shown, deduped across chains.
 *
 * Scoped to the category on purpose — the accounts page shows one category at a time, so offering
 * every tracked account would offer accounts that cannot appear in the table. That scoping is why
 * this cannot simply reuse history's list, which is drawn from the events instead.
 */
export function useBlockchainAccountOptions(category: MaybeRefOrGetter<string>): AccountFieldOptions & {
  readonly options: ComputedRef<AccountOption[]>;
} {
  const { getAccountsByCategory } = useBlockchainAccountData();
  const { getAddressName } = useAddressNameResolution();
  const { scrambleAddress } = useScramble();

  const accountsByCategory = getAccountsByCategory(category);

  const options = computed<AccountOption[]>(() => {
    const byAddress = new Map<string, AccountOption>();
    for (const item of get(accountsByCategory)) {
      const address = getAccountAddress(item);
      if (byAddress.has(address))
        continue;

      // An xpub is named by the account itself. Anything else resolves through the address book
      // (an ENS or alias name), falling back to the label the account was tracked under: alias
      // names can be switched off entirely, and a non-EVM account rarely has one, so without the
      // fallback a named account read as a bare address here while its table row read as its name.
      const name = isXpubAccount(item)
        ? getAccountLabel(item)
        : getAddressName(address, getChain(item)) ?? item.label;
      byAddress.set(address, {
        address,
        name: name && name !== address ? name : undefined,
        tags: item.tags ?? [],
      });
    }
    return [...byAddress.values()];
  });

  const byAddress = computed<Map<string, AccountOption>>(
    () => new Map(get(options).map(option => [option.address, option])),
  );
  const addresses = computed<string[]>(() => get(options).map(option => option.address));

  function shortAddress(address: string): string {
    return truncateAddress(scrambleAddress(address), 4);
  }

  return {
    options,
    resolveCaption: (address: string): string | undefined =>
      // With no name the label is the address itself, so a caption would only repeat it.
      get(byAddress).get(address)?.name ? shortAddress(address) : undefined,
    // Lowercased because the search box lowercases what is typed, and matched on the raw address
    // rather than the shown one: what the user pastes is the full, unscrambled address.
    resolveKeywords: (address: string): string | undefined => {
      const option = get(byAddress).get(address);
      return option && `${option.address} ${option.name ?? ''} ${option.tags.join(' ')}`.toLowerCase();
    },
    resolveLabel: (address: string): string => get(byAddress).get(address)?.name ?? shortAddress(address),
    suggest: (): string[] => get(addresses),
  };
}
