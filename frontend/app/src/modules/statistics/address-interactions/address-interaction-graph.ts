import type { AddressInteraction } from './address-interaction-types';

export interface InteractionNode {
  id: string;
  chains: string[];
  address: string;
}

export interface ChainActivity {
  chain: string;
  txHashes: string[];
  /** The transactions among `txHashes` that are a leg of a matched bridge. */
  bridgeTxHashes: string[];
}

/** Every transaction two addresses share, on any chain. */
export interface InteractionConnection {
  id: string;
  source: InteractionNode;
  target: InteractionNode;
  /** One entry per chain the pair shares a transaction on, ordered by chain id. */
  activity: ChainActivity[];
  txCount: number;
  /** Whether a matched bridge links the pair, as opposed to a transaction both addresses appear in. */
  isBridge: boolean;
}

export interface InteractionGraph {
  nodes: InteractionNode[];
  connections: InteractionConnection[];
}

/** Shared transactions of a connection, restricted to one chain when `chain` is set. */
export function transactionsOn(connection: InteractionConnection, chain?: string): number {
  if (!chain)
    return connection.txCount;
  return connection.activity.find(entry => entry.chain === chain)?.txHashes.length ?? 0;
}

/** Whether one end of the connection is the given address. */
export function touches(connection: InteractionConnection, nodeId?: string): boolean {
  return connection.source.id === nodeId || connection.target.id === nodeId;
}

/** How many connections each address has among `connections`. */
export function degreesOf(connections: Iterable<InteractionConnection>): Map<string, number> {
  const degrees = new Map<string, number>();
  for (const { source, target } of connections) {
    degrees.set(source.id, (degrees.get(source.id) ?? 0) + 1);
    degrees.set(target.id, (degrees.get(target.id) ?? 0) + 1);
  }
  return degrees;
}

/**
 * Builds one connection per address pair from the per-transaction interactions.
 *
 * @remarks
 * The API reports one row per chain, pair and transaction. Folding the chains into one connection
 * keeps a pair active on five chains as one relation, while `activity` keeps the per-chain detail.
 * A matched bridge puts each address on its own chain and records each leg's transaction under the
 * chain it happened on.
 * Nodes and connections come back sorted, so the same input always gives the same order.
 */
export function createAddressInteractionGraph(interactions: readonly AddressInteraction[]): InteractionGraph {
  const nodes = new Map<string, InteractionNode>();
  const connections = new Map<string, InteractionConnection>();
  const txHashes = new Map<string, Map<string, Set<string>>>();
  const bridgeHashes = new Set<string>();

  function node(chain: string, address: string): InteractionNode {
    let result = nodes.get(address);
    if (!result) {
      result = { address, chains: [], id: address };
      nodes.set(address, result);
    }
    if (!result.chains.includes(chain))
      result.chains.push(chain);
    return result;
  }

  function record(id: string, chain: string, txHash: string, bridge = false): void {
    const byChain = txHashes.get(id)!;
    const hashes = byChain.get(chain) ?? new Set<string>();
    hashes.add(txHash);
    byChain.set(chain, hashes);
    if (bridge)
      bridgeHashes.add(JSON.stringify([id, chain, txHash]));
  }

  for (const { chain, source: from, target: to, targetChain, targetTxHash, txHash } of interactions) {
    if (from === to)
      continue;

    const fromNode = node(chain, from);
    const toNode = node(targetChain ?? chain, to);
    const [source, target] = from < to ? [fromNode, toNode] : [toNode, fromNode];
    const id = JSON.stringify([source.id, target.id]);
    if (!connections.has(id)) {
      connections.set(id, { activity: [], id, isBridge: false, source, target, txCount: 0 });
      txHashes.set(id, new Map());
    }
    const isBridge = targetChain !== undefined && targetTxHash !== undefined;
    record(id, chain, txHash, isBridge);
    if (isBridge) {
      record(id, targetChain, targetTxHash, true);
      connections.get(id)!.isBridge = true;
    }
  }

  for (const [id, byChain] of txHashes) {
    const connection = connections.get(id)!;
    connection.activity = [...byChain]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([chain, hashes]) => {
        const sorted = [...hashes].sort();
        return { bridgeTxHashes: sorted.filter(hash => bridgeHashes.has(JSON.stringify([id, chain, hash]))), chain, txHashes: sorted };
      });
    connection.txCount = connection.activity.reduce((sum, entry) => sum + entry.txHashes.length, 0);
  }

  const sortedNodes = [...nodes.values()].sort((a, b) => a.id.localeCompare(b.id));
  for (const item of sortedNodes)
    item.chains.sort();

  return {
    connections: [...connections.values()].sort((a, b) => a.id.localeCompare(b.id)),
    nodes: sortedNodes,
  };
}
