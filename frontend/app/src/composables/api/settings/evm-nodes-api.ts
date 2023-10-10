import { type ActionResult } from '@rotki/common/lib/data';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';
import { type EvmRpcNode, EvmRpcNodeList } from '@/types/settings/rpc';

export const useEvmNodesApi = (chain: Blockchain = Blockchain.ETH) => {
  const url = `/blockchains/${chain}/nodes`;

  const fetchEvmNodes = async (): Promise<EvmRpcNodeList> => {
    const response = await api.instance.get<ActionResult<EvmRpcNodeList>>(url);
    return EvmRpcNodeList.parse(handleResponse(response));
  };

  const addEvmNode = async (
    node: Omit<EvmRpcNode, 'identifier'>
  ): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      url,
      snakeCaseTransformer(node),
      {
        validateStatus: validStatus
      }
    );
    return handleResponse(response);
  };

  const editEvmNode = async (node: EvmRpcNode): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      url,
      snakeCaseTransformer(node),
      {
        validateStatus: validStatus
      }
    );
    return handleResponse(response);
  };

  const deleteEvmNode = async (identifier: number): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(url, {
      data: snakeCaseTransformer({ identifier }),
      validateStatus: validStatus
    });
    return handleResponse(response);
  };

  return {
    fetchEvmNodes,
    addEvmNode,
    editEvmNode,
    deleteEvmNode
  };
};
