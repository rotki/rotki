import type { ComputedRef, Ref } from 'vue';
import type { AddressData, AssetBreakdown, BlockchainAccount } from '@/types/blockchain/accounts';
import { type BigNumber, type Blockchain, toSentenceCase } from '@rotki/common';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useAssetBalancesBreakdown } from '@/modules/balances/use-asset-balances-breakdown';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatusStore } from '@/store/status';
import { isBlockchain } from '@/types/blockchain/chains';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';

export interface AssetLocation extends AssetBreakdown {
  readonly account?: BlockchainAccount;
  readonly label: string;
}

export type AssetLocations = AssetLocation[];

interface UseAssetLocationsDataOptions {
  identifier: Ref<string>;
  locationFilter: Ref<string>;
  onlyTags: Ref<string[]>;
  selectedAccounts: Ref<BlockchainAccount<AddressData>[]>;
}

interface UseAssetLocationsDataReturn {
  assetLocations: ComputedRef<AssetLocations>;
  currencySymbol: Ref<string>;
  detailsLoading: Ref<boolean>;
  matchChain: (location: string) => Blockchain | undefined;
  totalValue: ComputedRef<BigNumber>;
  visibleAssetLocations: ComputedRef<AssetLocations>;
}

export function useAssetLocationsData(options: UseAssetLocationsDataOptions): UseAssetLocationsDataReturn {
  const { identifier, locationFilter, onlyTags, selectedAccounts } = options;

  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { detailsLoading } = storeToRefs(useStatusStore());
  const { getAccountByAddress } = useBlockchainAccountsStore();
  const { addressNameSelector } = useAddressesNamesStore();

  const { assetPriceInfo } = useAggregatedBalances();
  const { getChainName, matchChain } = useSupportedChains();
  const { useAssetBreakdown } = useAssetBalancesBreakdown();

  const totalValue = computed<BigNumber>(() => get(assetPriceInfo(identifier)).value);

  const assetLocations = computed<AssetLocations>(() => {
    const breakdowns = get(useAssetBreakdown(get(identifier)));
    return breakdowns.map((item: AssetBreakdown) => {
      const account = item.address ? getAccountByAddress(item.address, item.location) : undefined;
      return {
        ...item,
        account,
        label: account?.label ?? '',
      };
    });
  });

  const visibleAssetLocations = computed<AssetLocations>(() => {
    const locations = get(assetLocations).map(item => ({
      ...item,
      label:
        (isBlockchain(item.location) ? get(addressNameSelector(item.address, item.location)) : null)
        || item.label
        || item.address,
    }));

    const tagsFilter = get(onlyTags);
    const location = get(locationFilter);
    const accounts = get(selectedAccounts);

    return locations.filter((assetLocation) => {
      const tags = assetLocation.tags ?? [];
      const includedInTags = tagsFilter.every(tag => tags.includes(tag));
      const currentLocation = assetLocation.location;
      const locationToCheck = get(getChainName(currentLocation));
      const locationMatches = !location || locationToCheck === toSentenceCase(location);
      const accountMatches = accounts.length === 0 || accounts.some(account =>
        getAccountAddress(account) === assetLocation.address,
      );

      return includedInTags && locationMatches && accountMatches;
    });
  });

  return {
    assetLocations,
    currencySymbol,
    detailsLoading,
    matchChain,
    totalValue,
    visibleAssetLocations,
  };
}
