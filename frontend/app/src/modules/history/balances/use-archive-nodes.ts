import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { useEvmNodesApi } from '@/modules/settings/api/use-evm-nodes-api';

interface ArchiveProbe {
  chain: string;
  hasArchive: boolean;
}

interface UseArchiveNodesReturn {
  loading: Readonly<Ref<boolean>>;
  hasArchiveNode: (chain: MaybeRefOrGetter<string | undefined>) => ComputedRef<boolean>;
}

/**
 * Resolves which of the given EVM chains have an archive RPC node connected. The balance divergence
 * check queries on-chain balances at historical blocks, which the backend only serves when an
 * archive node is available (otherwise it returns 409). The panel uses this to guide the user
 * before running a query that would fail.
 */
export function useArchiveNodes(chains: MaybeRefOrGetter<string[]>): UseArchiveNodesReturn {
  const chainsWithArchiveNode = ref<string[]>([]);
  const loading = shallowRef<boolean>(false);

  async function refresh(list: string[]): Promise<void> {
    if (list.length === 0) {
      set(chainsWithArchiveNode, []);
      return;
    }

    set(loading, true);
    try {
      const results = await Promise.allSettled(
        list.map(async (chain): Promise<ArchiveProbe> => ({
          chain,
          hasArchive: (await useEvmNodesApi(chain).fetchEvmNodes()).some(node => node.isArchive),
        })),
      );
      set(chainsWithArchiveNode, results
        .filter((result): result is PromiseFulfilledResult<ArchiveProbe> =>
          result.status === 'fulfilled' && result.value.hasArchive)
        .map(result => result.value.chain));
    }
    finally {
      set(loading, false);
    }
  }

  function hasArchiveNode(chain: MaybeRefOrGetter<string | undefined>): ComputedRef<boolean> {
    return computed<boolean>(() => {
      const value = toValue(chain);
      return !!value && get(chainsWithArchiveNode).includes(value);
    });
  }

  watchImmediate(() => toValue(chains), refresh);

  return {
    hasArchiveNode,
    loading: readonly(loading),
  };
}
