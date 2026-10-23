import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';

/** One token's details, looked up on its chain. */
export interface Erc20InfoSubject {
  readonly evmChain: string;
  readonly address: string;
}

/** Checking which asset database version is available. */
export const assetVersionsActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.ASSETS,
  part: ActivityPart.VERSIONS,
});

/** Applying an asset database update. */
export const assetUpdateActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.ASSETS,
  part: ActivityPart.UPDATE,
});

/** Importing user assets from a file. */
export const assetImportActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.ASSETS,
  part: ActivityPart.IMPORT,
});

/** Exporting the user's custom assets. */
export const assetExportActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.ASSETS,
  part: ActivityPart.EXPORT,
});

/** Resetting the asset database. */
export const assetResetActivity = defineActivity<void, readonly []>({
  key: () => [],
  kind: ActivityKind.ASSETS,
  part: ActivityPart.RESET,
});

/** One token's details, keyed by chain and address so two lookups never dedup. */
export const erc20InfoActivity = defineActivity<Erc20InfoSubject, readonly [string, string]>({
  key: subject => [subject.evmChain, subject.address],
  kind: ActivityKind.ASSETS,
  part: ActivityPart.ERC20,
});

/** Fetching the NFT asset list, and whether it bypasses the cache. */
export const nftAssetsActivity = defineActivity<{ ignoreCache: boolean }, readonly [ActivityPart]>({
  key: subject => [subject.ignoreCache ? ActivityPart.PULL : ActivityPart.CACHED],
  kind: ActivityKind.ASSETS,
  part: ActivityPart.NFTS,
});
