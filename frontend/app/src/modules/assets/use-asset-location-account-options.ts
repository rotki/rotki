import type { MaybeRefOrGetter } from 'vue';
import type { AssetLocation } from '@/modules/assets/use-asset-locations-data';
import type { AccountFieldOptions } from '@/modules/core/table/filters/shared/account-field';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { isBlockchain } from '@/modules/core/common/chains';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { useScramble } from '@/modules/settings/use-scramble';

/** One account holding this asset, as the account pill needs to read it. */
interface AccountOption {
  readonly address: string;
  /** Its tracked/ENS name, absent when it has none. */
  readonly name?: string;
  readonly tags: string[];
}

/**
 * The account pill's values for the per-asset locations table: the accounts this asset is actually
 * held in, taken from the breakdown the table already renders.
 *
 * Drawn from the rows rather than from every tracked account, which is what the selector it
 * replaces offered: an account that does not hold the asset can only ever empty the table, and the
 * rows are the domain this filter is drawn from. An exchange row carries no address and so offers
 * no account.
 */
export function useAssetLocationAccountOptions(rows: MaybeRefOrGetter<AssetLocation[]>): AccountFieldOptions {
  const { getAddressName } = useAddressNameResolution();
  const { scrambleAddress } = useScramble();

  // One pass over the rows rather than a lookup per call: a resolver runs once per candidate value
  // on every keystroke while the bar narrows.
  const byAddress = computed<Map<string, AccountOption>>(() => {
    const map = new Map<string, AccountOption>();
    for (const row of toValue(rows)) {
      if (!row.address || map.has(row.address))
        continue;

      // The same name the row shows: an address-book or ENS name where the location is a chain,
      // else the label the account was tracked under.
      const name = (isBlockchain(row.location) ? getAddressName(row.address, row.location) : undefined)
        ?? row.label;
      map.set(row.address, {
        address: row.address,
        name: name && name !== row.address ? name : undefined,
        tags: row.tags ?? [],
      });
    }
    return map;
  });

  const addresses = computed<string[]>(() => [...get(byAddress).keys()]);

  function shortAddress(address: string): string {
    return truncateAddress(scrambleAddress(address), 4);
  }

  return {
    // With no name the label is the address itself, so a caption would only repeat it.
    resolveCaption: (address: string): string | undefined =>
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
