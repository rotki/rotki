import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { AddressData, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { LocationLabel } from '@/modules/core/common/location';
import { getTextToken } from '@rotki/common';
import { hasAccountAddress } from '@/modules/accounts/account-helpers';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useHistoryStore } from '@/modules/history/use-history-store';

interface UseLocationLabelsReturn {
  locationLabelOptions: ComputedRef<LocationLabel[]>;
  getBlockchainLocation: (location: string) => string | undefined;
  getTags: (item: LocationLabel) => string[];
  getTrackedAccountLabel: (item: LocationLabel) => string | undefined;
  getAccountName: (item: LocationLabel) => string | undefined;
  isAccountNamePending: (item: LocationLabel) => boolean;
  filter: (item: LocationLabel, queryText: string) => boolean;
}

/**
 * Resolves the option list, tracked-account metadata (tags, custom label) and the search filter for
 * an EVM location-label picker. Kept UI-free so the matching logic can be tested on its own.
 *
 * @param options optional explicit option list; falls back to the tracked history location labels.
 */
export function useLocationLabels(options: MaybeRefOrGetter<LocationLabel[] | undefined>): UseLocationLabelsReturn {
  const { locationLabels: storeLocationLabels } = storeToRefs(useHistoryStore());
  const { allTxChainsInfo, matchChain } = useSupportedChains();
  const txChainIds = useArrayMap(allTxChainsInfo, x => x.id);
  const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
  const { getAddressName, isAddressNamePending } = useAddressNameResolution();

  const locationLabelOptions = computed<LocationLabel[]>(() => toValue(options) ?? get(storeLocationLabels));

  const accounts = computed<BlockchainAccount<AddressData>[]>(() =>
    Object.values(get(accountsPerChain))
      .flatMap(x => x)
      .filter(hasAccountAddress),
  );

  function getBlockchainLocation(location: string): string | undefined {
    const chain = matchChain(location);
    if (!chain)
      return undefined;

    if (!get(txChainIds).includes(chain))
      return undefined;

    return chain;
  }

  function getRegisteredAccounts(item: LocationLabel): BlockchainAccount<AddressData>[] {
    const chain = getBlockchainLocation(item.location);

    if (!chain)
      return [];

    return get(accounts).filter(acc => getAccountAddress(acc) === item.locationLabel && acc.chain === chain);
  }

  function getTags(item: LocationLabel): string[] {
    const registeredAccounts = getRegisteredAccounts(item);
    if (registeredAccounts.length === 0)
      return [];

    return registeredAccounts[0].tags ?? [];
  }

  function getTrackedAccountLabel(item: LocationLabel): string | undefined {
    const label = getRegisteredAccounts(item)[0]?.label;
    return label && label !== item.locationLabel ? label : undefined;
  }

  /** The human name to show for an item: the tracked account's custom label, else its address-book/ENS name. */
  function getAccountName(item: LocationLabel): string | undefined {
    const trackedLabel = getTrackedAccountLabel(item);
    if (trackedLabel)
      return trackedLabel;

    const chain = getBlockchainLocation(item.location);
    if (!chain)
      return undefined;

    return getAddressName(item.locationLabel, chain) ?? undefined;
  }

  /** True while the item has no tracked label and its alias/ENS name is still being fetched. */
  function isAccountNamePending(item: LocationLabel): boolean {
    if (getTrackedAccountLabel(item))
      return false;

    const chain = getBlockchainLocation(item.location);
    if (!chain)
      return false;

    return isAddressNamePending(item.locationLabel, chain);
  }

  function filter(item: LocationLabel, queryText: string): boolean {
    const locationLabel = getTextToken(item.locationLabel);
    const query = getTextToken(queryText);

    if (locationLabel.includes(query))
      return true;

    const chain = getBlockchainLocation(item.location);

    if (!chain)
      return false;

    const text = getTextToken(getAddressName(item.locationLabel, chain) ?? '');
    const trackedAccountLabel = getTextToken(getTrackedAccountLabel(item) ?? '');

    if (text.includes(query) || trackedAccountLabel.includes(query))
      return true;

    const tags = getTags(item);
    return tags
      .map(tag => getTextToken(tag))
      .join(' ')
      .includes(query);
  }

  return {
    filter,
    getAccountName,
    getBlockchainLocation,
    getTags,
    getTrackedAccountLabel,
    isAccountNamePending,
    locationLabelOptions,
  };
}
