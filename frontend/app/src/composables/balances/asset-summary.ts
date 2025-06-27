import type { AssetProtocolBalances } from '@/types/blockchain/balances';
import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import {
  aggregateSourceBalances,
  createAssetBalanceFromAggregated,
  processCollectionGrouping,
  sortDesc,
} from '@/composables/balances/balance-transformations';

/**
 * Configuration for asset sources and associations
 */
export interface AssetSourceConfig {
  /** Asset protocol balances from different sources */
  sources: Record<string, AssetProtocolBalances>;
  /** Map of associated assets */
  associatedAssets: Record<string, string>;
}

/**
 * Configuration for asset filtering
 */
export interface AssetFilterConfig {
  /** Function to check if an asset is ignored */
  isAssetIgnored: (identifier: string) => boolean;
  /** Whether to hide ignored assets */
  hideIgnored: boolean;
}

/**
 * Configuration for not grouping collections
 */
interface NoGroupCollectionConfig {
  /** Whether to group collections */
  groupCollections: false;
}

/**
 * Configuration for collection grouping
 */
interface GroupCollectionConfig {
  /** Whether to group collections */
  groupCollections: true;
  useCollectionId: (asset: string) => { value: string | undefined };
  useCollectionMainAsset: (collectionId: string) => { value: string | undefined };
}

/**
 * Represents a configuration for a collection, which can either be a configuration
 * without groups or a configuration with groups.
 *
 * The `CollectionConfig` type is a union type that allows specifying one of the following:
 *   - `NoGroupCollectionConfig`: Represents a collection that is not grouped.
 *   - `GroupCollectionConfig`: Represents a collection that is grouped by certain criteria.
 *
 * Use this type to define the input configuration for operations requiring collection setups,
 * and to ensure proper validation and alignment with collection-related functionalities.
 */
export type CollectionConfig = NoGroupCollectionConfig | GroupCollectionConfig;

/**
 * Configuration for asset pricing
 */
export interface PricingConfig {
  /** Function to get price for an asset */
  getAssetPrice: (asset: string, defaultValue: BigNumber) => BigNumber;
  /** Default value for no price */
  noPrice: BigNumber;
}

/**
 * Summarizes asset protocols from different sources
 */
export function summarizeAssetProtocols(
  sourceConfig: AssetSourceConfig,
  filterConfig: AssetFilterConfig,
  pricingConfig: PricingConfig,
  collectionConfig: CollectionConfig,
): AssetBalanceWithPrice[] {
  const aggregatedBalances = aggregateSourceBalances(
    sourceConfig.sources,
    sourceConfig.associatedAssets,
    filterConfig.isAssetIgnored,
    filterConfig.hideIgnored,
  );

  const { groupCollections } = collectionConfig;
  const getAssetPrice = pricingConfig.getAssetPrice;
  const noPrice = pricingConfig.noPrice;

  if (!groupCollections) {
    return Object.entries(aggregatedBalances)
      .map(([asset, protocolBalances]) =>
        createAssetBalanceFromAggregated(asset, protocolBalances, asset => getAssetPrice(asset, noPrice)),
      )
      .sort((a, b) => sortDesc(a.usdValue, b.usdValue));
  }

  const { useCollectionId, useCollectionMainAsset } = collectionConfig;

  return processCollectionGrouping(
    aggregatedBalances,
    useCollectionId,
    useCollectionMainAsset,
    getAssetPrice,
    noPrice,
  );
}
