import { ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';
import { EthereumRpcNode, EthereumRpcNodeList } from '@/types/settings';

export const useEthNodesApi = () => {
  const fetchEthereumNodes = async (): Promise<EthereumRpcNodeList> => {
    const response = await api.instance.get<ActionResult<EthereumRpcNodeList>>(
      '/blockchains/ETH/nodes'
    );
    return EthereumRpcNodeList.parse(handleResponse(response));
  };

  const addEthereumNode = async (
    node: Omit<EthereumRpcNode, 'identifier'>
  ): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      '/blockchains/ETH/nodes',
      axiosSnakeCaseTransformer(node),
      {
        validateStatus: validStatus
      }
    );
    return handleResponse(response);
  };

  const editEthereumNode = async (node: EthereumRpcNode): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/blockchains/ETH/nodes',
      axiosSnakeCaseTransformer(node),
      {
        validateStatus: validStatus
      }
    );
    return handleResponse(response);
  };

  const deleteEthereumNode = async (identifier: number): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/blockchains/ETH/nodes',
      {
        data: axiosSnakeCaseTransformer({ identifier }),
        validateStatus: validStatus
      }
    );
    return handleResponse(response);
  };

  return {
    fetchEthereumNodes,
    addEthereumNode,
    editEthereumNode,
    deleteEthereumNode
  };
};
