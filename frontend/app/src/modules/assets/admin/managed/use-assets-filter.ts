import type { Ref, WritableComputedRef } from 'vue';
import type { MatchedKeyword } from '@/modules/core/table/filtering';
import type { ParamSource } from '@/modules/core/table/param-sources';
import { IgnoredAssetHandlingType, type IgnoredAssetsHandlingType, isIgnoredAssetsHandling } from '@/modules/assets/types';
import { boolParam, enumParam, type PillParams, refParams, toPillParams } from '@/modules/core/table/param-refs';

/** The wire keys the managed assets table filters on, which the URL carries too. */
export const AssetFilterKeys = {
  ADDRESS: 'address',
  ASSET_FLAG: 'assetFlag',
  ASSET_TYPE: 'assetType',
  CHAIN: 'evmChain',
  IDENTIFIER: 'identifiers',
  NAME: 'name',
  SYMBOL: 'symbol',
} as const;

type AssetFilterKey = typeof AssetFilterKeys[keyof typeof AssetFilterKeys];

export type Filters = MatchedKeyword<AssetFilterKey>;

/** The three refs the status filters live in, each its own so each is one declaration. */
export interface ManagedAssetStatus {
  ignoredAssetsHandling: Ref<IgnoredAssetsHandlingType>;
  onlyShowOwned: Ref<boolean>;
  onlyShowWhitelisted: Ref<boolean>;
}

/**
 * The three filters the status dropdown used to hold. They are params rather than part of the
 * filter bag above: two are booleans, which the bag has no form for, and the handling has a default
 * the backend needs stated even when no pill says it.
 *
 * A url is anyone's to write, and the handling reaches both the request and the ignored pill's
 * label, so an unrecognised one falls back to the default rather than being sent on.
 */
export function managedAssetStatusParams(status: ManagedAssetStatus): {
  source: ParamSource;
  pillParams: WritableComputedRef<PillParams>;
} {
  const spec = {
    ignoredAssetsHandling: enumParam(
      status.ignoredAssetsHandling,
      isIgnoredAssetsHandling,
      IgnoredAssetHandlingType.EXCLUDE,
    ),
    showUserOwnedAssetsOnly: boolParam(status.onlyShowOwned),
    showWhitelistedAssetsOnly: boolParam(status.onlyShowWhitelisted),
  };

  return {
    pillParams: toPillParams(spec),
    source: refParams(spec, { to: 'both' }),
  };
}
