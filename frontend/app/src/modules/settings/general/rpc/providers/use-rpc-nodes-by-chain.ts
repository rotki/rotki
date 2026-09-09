import type { BlockchainRpcNode } from '@/modules/settings/types/rpc';
import { useEvmNodesApi } from '@/modules/settings/api/use-evm-nodes-api';

export interface RpcNodesByChain {
  nodes: Record<string, BlockchainRpcNode[]>;
  /** The chains whose node list could not be read, which are not safe to plan against. */
  unreadable: string[];
}

interface UseRpcNodesByChainReturn {
  readNodes: (chains: string[]) => Promise<RpcNodesByChain>;
}

/**
 * Reads several chains' node lists at once.
 *
 * @remarks
 * A chain that cannot be read is named rather than reported as empty: the two look the same to a
 * caller planning against them, and "this chain has no nodes" is the answer that silently does the
 * wrong thing.
 */
export function useRpcNodesByChain(): UseRpcNodesByChainReturn {
  async function readNodes(chains: string[]): Promise<RpcNodesByChain> {
    const results = await Promise.allSettled(chains.map(async chain => ({
      chain,
      nodes: await useEvmNodesApi(chain).fetchEvmNodes(),
    })));

    const read: RpcNodesByChain = { nodes: {}, unreadable: [] };
    results.forEach((result, index) => {
      if (result.status === 'fulfilled')
        read.nodes[result.value.chain] = result.value.nodes;
      else
        read.unreadable.push(chains[index]);
    });
    return read;
  }

  return { readNodes };
}
