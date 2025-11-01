import type { ActionResult } from '@rotki/common';
import type { LidoCsmNodeOperator, LidoCsmNodeOperatorMetrics, LidoCsmNodeOperatorPayload } from '@/types/staking';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus, validWithSessionStatus } from '@/services/utils';

interface UseLidoCsmApiReturn {
  listNodeOperators: () => Promise<LidoCsmNodeOperator[]>;
  addNodeOperator: (payload: LidoCsmNodeOperatorPayload) => Promise<LidoCsmNodeOperator[]>;
  deleteNodeOperator: (payload: LidoCsmNodeOperatorPayload) => Promise<LidoCsmNodeOperator[]>;
}

const BASE_PATH = '/lido-csm/node-operators';

interface ApiNodeOperatorResponse {
  address: string;
  nodeOperatorId?: number;
  node_operator_id?: number;
  metrics?: LidoCsmNodeOperatorMetrics | null;
}

interface ApiNodeOperatorPayload {
  address: string;
  node_operator_id: number;
}

function toApiPayload(payload: LidoCsmNodeOperatorPayload): ApiNodeOperatorPayload {
  return {
    address: payload.address,
    node_operator_id: payload.nodeOperatorId,
  };
}

function fromApiResponse(entries: ApiNodeOperatorResponse[]): LidoCsmNodeOperator[] {
  const result: LidoCsmNodeOperator[] = [];
  for (const entry of entries) {
    const nodeOperatorId = entry.nodeOperatorId ?? entry.node_operator_id;
    if (nodeOperatorId === undefined)
      continue;

    result.push({
      address: entry.address,
      nodeOperatorId,
      metrics: entry.metrics ?? null,
    });
  }
  return result;
}

export function useLidoCsmApi(): UseLidoCsmApiReturn {
  const listNodeOperators = async (): Promise<LidoCsmNodeOperator[]> => {
    const response = await api.instance.get<ActionResult<ApiNodeOperatorResponse[]>>(BASE_PATH, {
      validateStatus: validWithSessionStatus,
    });

    return fromApiResponse(handleResponse(response));
  };

  const addNodeOperator = async (payload: LidoCsmNodeOperatorPayload): Promise<LidoCsmNodeOperator[]> => {
    const response = await api.instance.put<ActionResult<ApiNodeOperatorResponse[]>>(BASE_PATH, toApiPayload(payload), {
      validateStatus: validStatus,
    });

    return fromApiResponse(handleResponse(response));
  };

  const deleteNodeOperator = async (payload: LidoCsmNodeOperatorPayload): Promise<LidoCsmNodeOperator[]> => {
    const response = await api.instance.request<ActionResult<ApiNodeOperatorResponse[]>>({
      method: 'delete',
      url: BASE_PATH,
      data: toApiPayload(payload),
      validateStatus: validStatus,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return fromApiResponse(handleResponse(response));
  };

  return {
    addNodeOperator,
    deleteNodeOperator,
    listNodeOperators,
  };
}
