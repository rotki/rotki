import type { ComputedRef, MaybeRef, Ref } from 'vue';
import { useEvmNodesApi } from '@/composables/api/settings/evm-nodes-api';
import { useSupportedChains } from '@/composables/info/chains';

interface UseArchiveNodesReturn {
  chainsWithArchiveNodes: Ref<string[]>;
  hasArchiveNode: (chain: MaybeRef<string>) => ComputedRef<boolean>;
  loading: Ref<boolean>;
  refresh: () => Promise<void>;
}

export function useArchiveNodes(): UseArchiveNodesReturn {
  const chainsWithArchiveNodes = ref<string[]>([]);
  const loading = ref<boolean>(false);

  const { txEvmChains } = useSupportedChains();

  async function refresh(): Promise<void> {
    set(loading, true);

    try {
      const evmChains = get(txEvmChains);

      const results = await Promise.allSettled(
        evmChains.map(async (chainInfo) => {
          const chain = chainInfo.id;
          const api = useEvmNodesApi(chain);
          const nodes = await api.fetchEvmNodes();
          const hasArchive = nodes.some(node => node.isArchive);
          return { chainId: chain, hasArchive };
        }),
      );

      const chains = results
        .filter((r): r is PromiseFulfilledResult<{ chainId: string; hasArchive: boolean }> =>
          r.status === 'fulfilled' && r.value.hasArchive)
        .map(r => r.value.chainId);

      set(chainsWithArchiveNodes, chains);
    }
    finally {
      set(loading, false);
    }
  }

  function hasArchiveNode(chain: MaybeRef<string>): ComputedRef<boolean> {
    return computed<boolean>(() => {
      const chainValue = get(chain);
      return get(chainsWithArchiveNodes).includes(chainValue);
    });
  }

  return {
    chainsWithArchiveNodes,
    hasArchiveNode,
    loading,
    refresh,
  };
}
