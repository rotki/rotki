import type { RouteLocationRaw } from 'vue-router';

export interface BucketEventsRouteOptions {
  asset: string;
  isChainAccount: boolean;
  location?: string;
  locationLabel?: string | null;
}

/**
 * Route to the reconciliation tab, optionally deep-linked to a single asset filter.
 *
 * @remarks
 * Deep-linking with an asset sets `view: 'all'` so pending or reconciled buckets for that asset
 * remain visible instead of being hidden under the Needs-attention tab.
 */
export function reconciliationRoute(asset?: string): RouteLocationRaw {
  return {
    name: '/history/data-issues/[[tab]]',
    params: { tab: 'reconciliation' },
    ...(asset ? { query: { asset, view: 'all' } } : {}),
  };
}

/**
 * Route to the history events view scoped to one reconciliation bucket.
 *
 * @remarks
 * Blockchain accounts filter via `addresses`, while non-chain accounts (such as exchanges) filter
 * via `locationLabels`, matching the query keys parsed by `history-event-query.ts`.
 */
export function bucketEventsRoute({
  asset,
  isChainAccount,
  location,
  locationLabel,
}: BucketEventsRouteOptions): RouteLocationRaw {
  const query: Record<string, string> = { asset };
  if (location) {
    query.location = location;
    if (locationLabel) {
      if (isChainAccount)
        query.addresses = locationLabel;
      else
        query.locationLabels = locationLabel;
    }
  }
  return { name: '/history/events/', query };
}

/** Route to the history events view scoped to a single event group from a bucket trace row. */
export function traceRowEventRoute(groupIdentifier: string, asset: string): RouteLocationRaw {
  return {
    name: '/history/events/',
    query: {
      asset,
      groupIdentifiers: groupIdentifier,
    },
  };
}
