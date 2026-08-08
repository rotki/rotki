import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { AddressData, AssetBreakdown, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import { type BigNumber, type Blockchain, toSentenceCase } from '@rotki/common';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useAssetBalancesBreakdown } from '@/modules/balances/use-asset-balances-breakdown';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';
import { isBlockchain } from '@/modules/core/common/chains';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useSetting } from '@/modules/settings/use-setting';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

export interface AssetLocation extends AssetBreakdown {
  readonly account?: BlockchainAccount;
  readonly label: string;
}

type AssetLocations = AssetLocation[];

interface UseAssetLocationsDataOptions {
  /** The asset identifier to look up locations for */
  identifier: MaybeRefOrGetter<string>;
  /** Filter locations by a specific location string */
  locationFilter: Ref<string>;
  /** Filter locations by matching any of these tags */
  onlyTags: Ref<string[]>;
  /** Filter locations by matching any of these accounts */
  selectedAccounts: Ref<BlockchainAccount<AddressData>[]>;
}

interface UseAssetLocationsDataReturn {
  assetLocations: ComputedRef<AssetLocations>;
  currencySymbol: Ref<string>;
  detailsLoading: ComputedRef<boolean>;
  matchChain: (location: string) => Blockchain | undefined;
  totalValue: ComputedRef<BigNumber>;
  visibleAssetLocations: ComputedRef<AssetLocations>;
}

export function useAssetLocationsData(options: UseAssetLocationsDataOptions): UseAssetLocationsDataReturn {
  const { identifier, locationFilter, onlyTags, selectedAccounts } = options;

  const currencySymbol = useSetting('currencySymbol');
  // Every source that can still be filling the breakdown this table renders.
  const { useIsActive } = useTaskCenter();
  const { loadingBlockchainBalances } = useBalancesLoading();
  const detailsLoading = logicOr(
    loadingBlockchainBalances,
    useIsActive(ActivityKind.EXCHANGE_BALANCES),
    useIsActive(ActivityKind.MANUAL_BALANCES),
  );
  const { getAccountByAddress } = useBlockchainAccountsStore();
  const { getAddressName } = useAddressNameResolution();

  const { getAssetPriceInfo } = useAggregatedBalances();
  const { getChainName, matchChain } = useSupportedChains();
  const { getAssetBreakdown } = useAssetBalancesBreakdown();

  const totalValue = computed<BigNumber>(() => getAssetPriceInfo(toValue(identifier)).value);

  const assetLocations = computed<AssetLocations>(() => {
    const breakdowns = getAssetBreakdown(toValue(identifier));
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
        ((isBlockchain(item.location) ? getAddressName(item.address, item.location) : null)
          ?? item.label)
        || item.address,
    }));

    const tagsFilter = get(onlyTags);
    const location = get(locationFilter);
    const accounts = get(selectedAccounts);

    return locations.filter((assetLocation) => {
      const tags = assetLocation.tags ?? [];
      const includedInTags = tagsFilter.every(tag => tags.includes(tag));
      const currentLocation = assetLocation.location;
      const locationToCheck = getChainName(currentLocation);
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
