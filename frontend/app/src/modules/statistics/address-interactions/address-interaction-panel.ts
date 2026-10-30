import type { RouteLocationRaw } from 'vue-router';
import type { InteractionConnection, InteractionNode } from './address-interaction-graph';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useLocations } from '@/modules/core/common/use-locations';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

/** How many connection rows the side panel reveals at a time; each row mounts up to two `HashLink`s. */
export const CONNECTION_PAGE_SIZE = 50;

/** Strongest relations first: more shared transactions, then the graph's own stable order. */
export function sortByActivity(connections: readonly InteractionConnection[]): InteractionConnection[] {
  return [...connections].sort((a, b) => b.txHashes.length - a.txHashes.length || a.id.localeCompare(b.id));
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
 * connection's location is part of the filter to keep this in step with the graph's per-chain
 * connections. A `location` of `undefined` leaves the filter off rather than send a value the
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

/**
 * Picks the chain to resolve an address's name on, so the panel shows the same name as the canvas.
 *
 * @remarks
 * An address may only be named on one of its chains. Only use this where no explorer link depends
 * on the chain, since the named chain can differ from the connection's.
 */
export function useNamedChain(): (address: string, chains: readonly string[]) => string {
  const { getAddressName } = useAddressNameResolution();
  return (address, chains) => chains.find(chain => getAddressName(address, chain)) ?? chains[0];
}
