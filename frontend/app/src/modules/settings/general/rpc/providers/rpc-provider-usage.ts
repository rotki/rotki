import type { BlockchainRpcNode } from '@/modules/settings/types/rpc';
import {
  detectRpcProvider,
  getRpcProvider,
  isRpcProviderEndpoint,
  maskRpcKey,
  RPC_PROVIDER_IDS,
  type RpcProviderId,
} from '@/modules/settings/general/rpc/providers/rpc-providers';

interface RpcProviderNode {
  chain: string;
  identifier: number;
  name: string;
}

export interface RpcProviderUsage {
  id: RpcProviderId;
  /**
   * The credential these nodes authenticate with, masked.
   *
   * @remarks
   * Empty when the endpoint sits on the provider's host but does not parse, which is the bucket a
   * hand-written variant of one of their urls falls into. Masked rather than raw so the whole key
   * never reaches component state.
   */
  key: string;
  name: string;
  /** Every node this credential holds, across every chain. */
  nodes: RpcProviderNode[];
}

/** Nodes are grouped by what they authenticate with, which for QuickNode is the endpoint plus token. */
function credentialOf(endpoint: string): { group: string; id: RpcProviderId; key: string } | undefined {
  const match = detectRpcProvider(endpoint);
  if (match) {
    const { endpointName = '', key } = match.credentials;
    return { group: `${match.providerId}:${endpointName}:${key}`, id: match.providerId, key: maskRpcKey(key) };
  }

  const id = RPC_PROVIDER_IDS.find(candidate => isRpcProviderEndpoint(endpoint, candidate));
  return id ? { group: `${id}:unparsed`, id, key: '' } : undefined;
}

/**
 * Groups the nodes a set of chains hold by the provider credential serving them.
 *
 * @remarks
 * One entry per key, not per provider: two keys of the same provider are two separate things to the
 * user, and merging them would let one removal take out both. Matched on the endpoint rather than on
 * a stored provider id, since nothing records where a node came from — a node added by hand years
 * ago counts the same as one this dialog wrote.
 *
 * @param nodesByChain - the nodes each chain holds
 * @returns one entry per credential that holds at least one node, in provider order
 */
export function groupNodesByProvider(nodesByChain: Record<string, BlockchainRpcNode[]>): RpcProviderUsage[] {
  const usages = new Map<string, RpcProviderUsage>();

  for (const [chain, chainNodes] of Object.entries(nodesByChain)) {
    for (const node of chainNodes) {
      const credential = credentialOf(node.endpoint);
      if (!credential)
        continue;

      const usage = usages.get(credential.group) ?? {
        id: credential.id,
        key: credential.key,
        name: getRpcProvider(credential.id).name,
        nodes: [],
      };
      usage.nodes.push({ chain, identifier: node.identifier, name: node.name });
      usages.set(credential.group, usage);
    }
  }

  return [...usages.values()].sort((a, b) =>
    RPC_PROVIDER_IDS.indexOf(a.id) - RPC_PROVIDER_IDS.indexOf(b.id) || a.key.localeCompare(b.key));
}
