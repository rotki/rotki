import type { BlockchainRpcNode } from '@/modules/settings/types/rpc';
import {
  buildRpcEndpoint,
  getRpcProvider,
  isRpcProviderEndpoint,
  type RpcProviderMatch,
} from '@/modules/settings/general/rpc/providers/rpc-providers';

export interface RpcProviderCandidate {
  chain: string;
  endpoint: string;
  /** The node this chain already holds on exactly this endpoint, which leaves nothing to do. */
  existing?: BlockchainRpcNode;
  name: string;
  /**
   * The node this chain holds on the same provider with different credentials.
   *
   * @remarks
   * This is a key the user is replacing, so the endpoint is updated in place rather than added
   * beside the old one, which would leave the chain holding a node that no longer authenticates.
   */
  outdated?: BlockchainRpcNode;
}

export interface RpcProviderPlan {
  /** One entry per chain the provider and rotki both support, in rotki's own chain order. */
  candidates: RpcProviderCandidate[];
  /** The chains rotki supports that this provider does not serve. */
  unsupported: string[];
}

/**
 * Names the node after its provider, since names are scoped to a chain's own list.
 *
 * @remarks
 * Nothing in the schema stops two nodes sharing a name, so this only keeps the list readable.
 */
function uniqueName(providerName: string, taken: string[]): string {
  if (!taken.includes(providerName))
    return providerName;

  let suffix = 2;
  while (taken.includes(`${providerName} (${suffix})`))
    suffix += 1;

  return `${providerName} (${suffix})`;
}

/**
 * Works out what one provider key can cover, given the chains rotki has and the nodes each one
 * already holds.
 *
 * @param match - the provider and credentials read off the pasted endpoint
 * @param chains - the chains rotki can manage nodes for, in the order the ui shows them
 * @param nodesByChain - the nodes each of those chains already has
 * @param preferredName - what to call the nodes, defaulting to the provider's own name; blank falls
 * back to that default, since the backend rejects an empty name
 * @returns the per-chain candidates, and the chains this provider cannot serve
 */
export function buildRpcProviderPlan(
  match: RpcProviderMatch,
  chains: string[],
  nodesByChain: Record<string, BlockchainRpcNode[]>,
  preferredName = '',
): RpcProviderPlan {
  const provider = getRpcProvider(match.providerId);
  const served = new Set(provider.chains);
  const wanted = preferredName.trim() || provider.name;
  const candidates: RpcProviderCandidate[] = [];
  const unsupported: string[] = [];

  for (const chain of chains) {
    const endpoint = served.has(chain) ? buildRpcEndpoint(match, chain) : undefined;
    if (!endpoint) {
      unsupported.push(chain);
      continue;
    }

    const nodes = nodesByChain[chain] ?? [];
    const onProvider = nodes.filter(node => isRpcProviderEndpoint(node.endpoint, match.providerId));
    candidates.push({
      chain,
      endpoint,
      existing: onProvider.find(node => node.endpoint === endpoint),
      name: uniqueName(wanted, nodes.map(node => node.name)),
      outdated: onProvider.find(node => node.endpoint !== endpoint),
    });
  }

  return { candidates, unsupported };
}

/**
 * The node a candidate is added as.
 *
 * @remarks
 * Owned with a weight of zero on purpose: owned nodes are tried before the weighted ones whatever
 * their weight, so nothing has to be taken from the user's own nodes to make this one count.
 *
 * A zero still leaves the chain's weights *proportionally* untouched rather than literally so: the
 * backend rescales every other node of the chain into `1 - weight` on insert, which is a no-op only
 * when they already sum to 100. rotki's shipped defaults do not (ethereum's sum to 115), so the
 * first insert renormalises them, and removing the node again does not put the old numbers back.
 */
export function toRpcNodePayload(candidate: RpcProviderCandidate): Omit<BlockchainRpcNode, 'identifier'> {
  return {
    active: true,
    blockchain: candidate.chain,
    endpoint: candidate.endpoint,
    name: candidate.name,
    owned: true,
    weight: 0,
  };
}
