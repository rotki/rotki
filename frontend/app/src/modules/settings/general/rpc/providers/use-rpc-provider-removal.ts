import type { Ref } from 'vue';
import { useEvmNodesApi } from '@/modules/settings/api/use-evm-nodes-api';
import { groupNodesByProvider, type RpcProviderUsage } from '@/modules/settings/general/rpc/providers/rpc-provider-usage';
import { useRpcNodesByChain } from '@/modules/settings/general/rpc/providers/use-rpc-nodes-by-chain';

interface RpcRemovalResult {
  failed: number;
  removed: number;
}

interface UseRpcProviderRemovalReturn {
  /** Whether a removal is in flight. */
  removing: Readonly<Ref<boolean>>;
  /** Re-reads the chains and regroups what each provider holds. */
  refresh: (chains: string[]) => Promise<void>;
  /** Deletes every node of one provider, and reports what could not be deleted. */
  removeAll: (usage: RpcProviderUsage) => Promise<RpcRemovalResult>;
  /** The providers that hold at least one node right now. */
  usages: Readonly<Ref<RpcProviderUsage[]>>;
}

/**
 * Tracks which providers hold nodes, and takes one out in a single action.
 *
 * @remarks
 * The counterpart to the fan-out: a key spread over a dozen chains would otherwise have to be
 * removed a dozen times, one chain tab at a time. Deletes are independent, so one failure does not
 * stop the rest — the count that comes back says how many survived.
 */
export function useRpcProviderRemoval(): UseRpcProviderRemovalReturn {
  const { readNodes } = useRpcNodesByChain();
  const usages = ref<RpcProviderUsage[]>([]);
  const removing = shallowRef<boolean>(false);

  async function refresh(chains: string[]): Promise<void> {
    const { nodes } = await readNodes(chains);
    set(usages, groupNodesByProvider(nodes));
  }

  async function removeAll(usage: RpcProviderUsage): Promise<RpcRemovalResult> {
    set(removing, true);
    let removed = 0;
    try {
      for (const node of usage.nodes) {
        try {
          await useEvmNodesApi(node.chain).deleteEvmNode(node.identifier);
          removed += 1;
        }
        catch {
          // counted as failed below; one chain refusing must not strand the others
        }
      }
    }
    finally {
      set(removing, false);
    }

    return { failed: usage.nodes.length - removed, removed };
  }

  return {
    refresh,
    removeAll,
    removing: readonly(removing),
    usages: shallowReadonly(usages),
  };
}
