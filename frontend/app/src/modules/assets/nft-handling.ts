/**
 * How an asset search treats NFTs.
 *
 * NFTs are searched by a query of their own, separate from the asset search, so all three states
 * choose which queries run rather than filter what comes back. That matters for `SHOW_ONLY`: both
 * result sets are ranked and truncated to the request's `limit` together, so a caller cannot get
 * "NFTs only" by filtering the response of an `INCLUDE` search — an asset ranking better than an
 * NFT pushes it out before it is ever returned.
 *
 * Kept in its own module rather than beside the search api: the values are shared by the api
 * layer, the search composable and the picker, and a spec that mocks the api module wholesale
 * would otherwise leave them undefined.
 */
export const NftHandling = {
  EXCLUDE: 'exclude',
  INCLUDE: 'include',
  SHOW_ONLY: 'show_only',
} as const;

export type NftHandling = typeof NftHandling[keyof typeof NftHandling];
