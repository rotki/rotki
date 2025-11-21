import type { ActionResult } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus, validWithSessionStatus } from '@/services/utils';
import {
  type LidoCsmNodeOperator,
  LidoCsmNodeOperatorListSchema,
  type LidoCsmNodeOperatorPayload,
  LidoCsmNodeOperatorPayloadSchema,
} from '@/types/staking';

interface UseLidoCsmApiReturn {
  listNodeOperators: () => Promise<LidoCsmNodeOperator[]>;
  addNodeOperator: (payload: LidoCsmNodeOperatorPayload) => Promise<LidoCsmNodeOperator[]>;
  deleteNodeOperator: (payload: LidoCsmNodeOperatorPayload) => Promise<LidoCsmNodeOperator[]>;
  refreshMetrics: () => Promise<LidoCsmNodeOperator[]>;
}

const BASE_PATH = '/lido-csm/node-operators';
const METRICS_PATH = '/lido-csm/metrics';

function toApiPayload(payload: LidoCsmNodeOperatorPayload): Record<string, unknown> {
  const validated = LidoCsmNodeOperatorPayloadSchema.parse(payload);
  return snakeCaseTransformer(validated);
}

export function useLidoCsmApi(): UseLidoCsmApiReturn {
  const listNodeOperators = async (): Promise<LidoCsmNodeOperator[]> => {
    const response = await api.instance.get<ActionResult<LidoCsmNodeOperator[]>>(BASE_PATH, {
      validateStatus: validWithSessionStatus,
    });

    return LidoCsmNodeOperatorListSchema.parse(handleResponse(response));
  };

  const addNodeOperator = async (payload: LidoCsmNodeOperatorPayload): Promise<LidoCsmNodeOperator[]> => {
    const response = await api.instance.put<ActionResult<LidoCsmNodeOperator[]>>(
      BASE_PATH,
      toApiPayload(payload),
      {
        validateStatus: validStatus,
      },
    );

    return LidoCsmNodeOperatorListSchema.parse(handleResponse(response));
  };

  const deleteNodeOperator = async (payload: LidoCsmNodeOperatorPayload): Promise<LidoCsmNodeOperator[]> => {
    const response = await api.instance.delete<ActionResult<LidoCsmNodeOperator[]>>(BASE_PATH, {
      data: toApiPayload(payload),
      validateStatus: validStatus,
    });

    return LidoCsmNodeOperatorListSchema.parse(handleResponse(response));
  };

  const refreshMetrics = async (): Promise<LidoCsmNodeOperator[]> => {
    const response = await api.instance.post<ActionResult<LidoCsmNodeOperator[]>>(
      METRICS_PATH,
      undefined,
      {
        validateStatus: validWithSessionStatus,
      },
    );

    return LidoCsmNodeOperatorListSchema.parse(handleResponse(response));
  };

  return {
    addNodeOperator,
    deleteNodeOperator,
    listNodeOperators,
    refreshMetrics,
  };
}
