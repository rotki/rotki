import { type ActionResult, Blockchain } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';
import { type EvmRpcNode, EvmRpcNodeList } from '@/types/settings/rpc';

interface UseEvmNodesApiReturn {
  fetchEvmNodes: () => Promise<EvmRpcNodeList>;
  addEvmNode: (node: Omit<EvmRpcNode, 'identifier'>) => Promise<boolean>;
  editEvmNode: (node: EvmRpcNode) => Promise<boolean>;
  deleteEvmNode: (identifier: number) => Promise<boolean>;
}

export function useEvmNodesApi(chain: Ref<Blockchain> = ref(Blockchain.ETH)): UseEvmNodesApiReturn {
  const url = computed<string>(() => `/blockchains/${get(chain)}/nodes`);

  const fetchEvmNodes = async (): Promise<EvmRpcNodeList> => {
    const response = await api.instance.get<ActionResult<EvmRpcNodeList>>(get(url));
    return EvmRpcNodeList.parse(handleResponse(response));
  };

  const addEvmNode = async (node: Omit<EvmRpcNode, 'identifier'>): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(get(url), snakeCaseTransformer(node), {
      validateStatus: validStatus,
    });
    return handleResponse(response);
  };

  const editEvmNode = async (node: EvmRpcNode): Promise<boolean> => {
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

  return {
    fetchEvmNodes,
    addEvmNode,
    editEvmNode,
    deleteEvmNode,
  };
}
