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
 * Drawn from the rows rather than from every tracked account: an account that does not hold the
 * asset can only ever empty the table. An exchange row carries no address and so offers no account.
 *
 * Each account is labelled with the same name its row shows, and matched on its raw address rather
 * than the shown one, since what a user pastes is the full, unscrambled address.
 */
export function useAssetLocationAccountOptions(rows: MaybeRefOrGetter<AssetLocation[]>): AccountFieldOptions {
  const { getAddressName } = useAddressNameResolution();
  const { scrambleAddress } = useScramble();

  const byAddress = computed<Map<string, AccountOption>>(() => {
    const map = new Map<string, AccountOption>();
    for (const row of toValue(rows)) {
      if (!row.address || map.has(row.address))
        continue;

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
    resolveCaption: (address: string): string | undefined =>
      get(byAddress).get(address)?.name ? shortAddress(address) : undefined,
    resolveKeywords: (address: string): string | undefined => {
      const option = get(byAddress).get(address);
      return option && `${option.address} ${option.name ?? ''} ${option.tags.join(' ')}`.toLowerCase();
    },
    resolveLabel: (address: string): string => get(byAddress).get(address)?.name ?? shortAddress(address),
    suggest: (): string[] => get(addresses),
  };
}
