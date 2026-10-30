import type { RouteLocationRaw } from 'vue-router';
import type { InteractionConnection, InteractionNode } from './address-interaction-graph';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';

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

/** The history events page filtered to exactly these transactions. */
export function historyEventsRoute(txHashes: readonly string[]): RouteLocationRaw {
  return { name: '/history/events/', query: { txRefs: [...txHashes] } };
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
