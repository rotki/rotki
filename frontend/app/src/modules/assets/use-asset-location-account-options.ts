import type { MaybeRefOrGetter } from 'vue';
import type { AssetLocation } from '@/modules/assets/use-asset-locations-data';
import type { AccountFieldOptions } from '@/modules/core/table/filters/shared/account-field';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { isBlockchain } from '@/modules/core/common/chains';
import { type AccountOption, useAccountOptionResolvers } from '@/modules/core/table/filters/shared/use-account-option-resolvers';

/**
 * The account pill's values for the per-asset locations table: the accounts this asset is actually
 * held in, taken from the breakdown the table already renders.
 *
 * Drawn from the rows rather than from every tracked account: an account that does not hold the
 * asset can only ever empty the table. An exchange row carries no address and so offers no account.
 *
 * Each account is labelled with the same name its row shows.
 */
export function useAssetLocationAccountOptions(rows: MaybeRefOrGetter<AssetLocation[]>): AccountFieldOptions {
  const { getAddressName } = useAddressNameResolution();

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

  return useAccountOptionResolvers(byAddress);
}
