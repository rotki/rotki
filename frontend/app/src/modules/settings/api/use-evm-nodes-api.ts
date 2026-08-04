import type { MaybeRefOrGetter } from 'vue';
import { Blockchain } from '@rotki/common';
import { api } from '@/modules/core/api/rotki-api';
import {
  type BlockchainRpcNode,
  BlockchainRpcNodeAddPayload,
  BlockchainRpcNodeEditPayload,
  BlockchainRpcNodeList,
} from '@/modules/settings/types/rpc';

interface UseEvmNodesApiReturn {
  fetchEvmNodes: () => Promise<BlockchainRpcNodeList>;
  addEvmNode: (node: Omit<BlockchainRpcNode, 'identifier'>) => Promise<boolean>;
  editEvmNode: (node: BlockchainRpcNode) => Promise<boolean>;
  deleteEvmNode: (identifier: number) => Promise<boolean>;
  reConnectNode: (identifier?: number) => Promise<boolean>;
}

export function useEvmNodesApi(chain: MaybeRefOrGetter<string> = Blockchain.ETH): UseEvmNodesApiReturn {
  const url = computed<string>(() => `/blockchains/${toValue(chain)}/nodes`);

  const fetchEvmNodes = async (): Promise<BlockchainRpcNodeList> => {
    const response = await api.get<BlockchainRpcNodeList>(get(url));
    return BlockchainRpcNodeList.parse(response);
  };

  const addEvmNode = async (node: Omit<BlockchainRpcNode, 'identifier'>): Promise<boolean> => api.put<boolean>(get(url), BlockchainRpcNodeAddPayload.parse(node));

  const editEvmNode = async (node: BlockchainRpcNode): Promise<boolean> => api.patch<boolean>(get(url), BlockchainRpcNodeEditPayload.parse(node));

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
