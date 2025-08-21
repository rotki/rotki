import type { Ref } from 'vue';
import { type ActionResult, Blockchain } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';
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
    const response = await api.instance.get<ActionResult<BlockchainRpcNodeList>>(get(url));
    return BlockchainRpcNodeList.parse(handleResponse(response));
  };

  const addEvmNode = async (node: Omit<BlockchainRpcNode, 'identifier'>): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(get(url), snakeCaseTransformer(node), {
      validateStatus: validStatus,
    });
    return handleResponse(response);
  };

  const editEvmNode = async (node: BlockchainRpcNode): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(get(url), snakeCaseTransformer(node), {
      validateStatus: validStatus,
    });
    return handleResponse(response);
  };

  const deleteEvmNode = async (identifier: number): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(get(url), {
      data: snakeCaseTransformer({ identifier }),
      validateStatus: validStatus,
    });
    return handleResponse(response);
  };

  const reConnectNode = async (identifier?: number): Promise<boolean> => {
    const response = await api.instance.post<ActionResult<boolean>>(get(url), snakeCaseTransformer({ identifier }), {
      validateStatus: validStatus,
    });
    return handleResponse(response);
  };

  return {
    addEvmNode,
    deleteEvmNode,
    editEvmNode,
    fetchEvmNodes,
    reConnectNode,
  };
}
