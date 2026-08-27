import type { BigNumber, Blockchain } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { AssetBreakdown, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
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
  /** Filter locations by the picked location, as its raw id (`kraken`, `polygon_pos`) */
  locationFilter: MaybeRefOrGetter<string>;
  /** Filter locations by matching any of these tags */
  onlyTags: MaybeRefOrGetter<string[]>;
  /** Filter locations by matching any of these account addresses */
  addresses: MaybeRefOrGetter<string[]>;
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
  const { addresses, identifier, locationFilter, onlyTags } = options;

  const currencySymbol = useSetting('currencySymbol');
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
  const { matchChain } = useSupportedChains();
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

    const tagsFilter = toValue(onlyTags);
    const location = toValue(locationFilter);
    const picked = toValue(addresses);

    return locations.filter((assetLocation) => {
      const tags = assetLocation.tags ?? [];
      const includedInTags = tagsFilter.every(tag => tags.includes(tag));
      const locationMatches = !location || assetLocation.location === location;
      const accountMatches = picked.length === 0 || picked.includes(assetLocation.address);

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
