import type { Ref } from 'vue';
import { Blockchain } from '@rotki/common';
import { api } from '@/modules/api/rotki-api';
import { type BlockchainRpcNode, BlockchainRpcNodeList } from '@/types/settings/rpc';

interface UseEvmNodesApiReturn {
  fetchEvmNodes: () => Promise<BlockchainRpcNodeList>;
  addEvmNode: (node: Omit<BlockchainRpcNode, 'identifier'>) => Promise<boolean>;
  editEvmNode: (node: BlockchainRpcNode) => Promise<boolean>;
  deleteEvmNode: (identifier: number) => Promise<boolean>;
  reConnectNode: (identifier?: number) => Promise<boolean>;
}

export function useEvmNodesApi(chain: Ref<Blockchain> = ref(Blockchain.ETH)): UseEvmNodesApiReturn {
  const url = computed<string>(() => `/blockchains/${get(chain)}/nodes`);

  const fetchEvmNodes = async (): Promise<BlockchainRpcNodeList> => {
    const response = await api.get<BlockchainRpcNodeList>(get(url));
    return BlockchainRpcNodeList.parse(response);
  };

  const addEvmNode = async (node: Omit<BlockchainRpcNode, 'identifier'>): Promise<boolean> => api.put<boolean>(get(url), node);

  const editEvmNode = async (node: BlockchainRpcNode): Promise<boolean> => api.patch<boolean>(get(url), node);

  const deleteEvmNode = async (identifier: number): Promise<boolean> => api.delete<boolean>(get(url), {
    body: { identifier },
  });

  const reConnectNode = async (identifier?: number): Promise<boolean> => api.post<boolean>(get(url), { identifier });

  return {
    addEvmNode,
    deleteEvmNode,
    editEvmNode,
    fetchEvmNodes,
    reConnectNode,
  };
}
