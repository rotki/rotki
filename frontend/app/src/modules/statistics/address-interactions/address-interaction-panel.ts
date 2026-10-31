import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import { useLocations } from '@/modules/core/common/use-locations';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { type InteractionConnection, type InteractionNode, transactionsOn } from './address-interaction-graph';

/** How many rows a paged side-panel list reveals at a time; each row mounts at least one `HashLink`. */
export const PAGE_SIZE = 50;

/**
 * Strongest relations first: more shared transactions on `chain` (all chains when unset).
 *
 * @remarks
 * The sort is stable, so ties keep the order they came in, which for the graph's connections is
 * already sorted by id.
 */
export function sortByActivity(connections: readonly InteractionConnection[], chain?: string): InteractionConnection[] {
  const weights = new Map(connections.map(connection => [connection, transactionsOn(connection, chain)]));
  return [...connections].sort((a, b) => weights.get(b)! - weights.get(a)!);
}

/**
 * The address on the far side of a connection, seen from the focused address.
 *
 * @returns `undefined` when no address is focused or the connection does not touch it.
 */
export function counterpartOf(connection: InteractionConnection, nodeId?: string): InteractionNode | undefined {
  if (connection.source.id === nodeId)
    return connection.target;
  if (connection.target.id === nodeId)
    return connection.source;
  return undefined;
}

/**
 * The history events page filtered to exactly these transactions, on one location when known.
 *
 * @remarks
 * `txRefs` does not restrict the location, and the same hash can exist on several chains, so the
 * chain's location is part of the filter to keep this in step with one chain of a connection's
 * activity. A `location` of `undefined` leaves the filter off rather than send a value the
 * history page would not recognise.
 */
export function historyEventsRoute(location: string | undefined, txHashes: readonly string[]): RouteLocationRaw {
  return { name: '/history/events/', query: { ...(location && { location }), txRefs: [...txHashes] } };
}

/**
 * Resolves a connection's chain id (`eth`) to the history location that holds its events (`ethereum`).
 *
 * @remarks
 * The interactions API names chains by blockchain id, while the history `location` filter only
 * accepts location identifiers, so the two cannot be passed through unchanged.
 */
export function useChainLocation(): (chain: string) => string | undefined {
  const { tradeLocations } = useLocations();
  const { matchChain } = useSupportedChains();
  return (chain) => {
    const blockchain = matchChain(chain);
    return blockchain ? get(tradeLocations).find(({ identifier }) => matchChain(identifier) === blockchain)?.identifier : undefined;
  };
}

interface PagedList<T> {
  shown: ComputedRef<T[]>;
  /** How many more rows the next page reveals; 0 when everything shows. */
  nextCount: ComputedRef<number>;
  showMore: () => void;
}

/**
 * Reveals a long list a page at a time.
 *
 * @param items - The full list.
 * @param limit - How many rows show; pass a ref the caller owns to keep it across unmounts.
 */
export function usePagedList<T>(items: MaybeRefOrGetter<readonly T[]>, limit: Ref<number> = ref<number>(PAGE_SIZE)): PagedList<T> {
  const shown = computed<T[]>(() => toValue(items).slice(0, get(limit)));
  const nextCount = computed<number>(() => Math.min(PAGE_SIZE, Math.max(0, toValue(items).length - get(limit))));

  function showMore(): void {
    set(limit, get(limit) + PAGE_SIZE);
  }

  return { nextCount, showMore, shown };
}
