import type { ActionResult } from '@rotki/common';
import type { AxiosResponse } from 'axios';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithSessionAndExternalService,
  validWithSessionStatus,
} from '@/services/utils';
import {
  type LidoCsmNodeOperator,
  LidoCsmNodeOperatorListSchema,
  type LidoCsmNodeOperatorPayload,
  LidoCsmNodeOperatorPayloadSchema,
} from '@/types/staking';

export interface LidoCsmApiResult {
  entries: LidoCsmNodeOperator[];
  message: string;
}

interface UseLidoCsmApiReturn {
  listNodeOperators: () => Promise<LidoCsmApiResult>;
  addNodeOperator: (payload: LidoCsmNodeOperatorPayload) => Promise<LidoCsmApiResult>;
  deleteNodeOperator: (payload: LidoCsmNodeOperatorPayload) => Promise<LidoCsmApiResult>;
  refreshMetrics: () => Promise<LidoCsmApiResult>;
}

const BASE_PATH = '/lido-csm/node-operators';
const METRICS_PATH = '/lido-csm/metrics';

function toApiPayload(payload: LidoCsmNodeOperatorPayload): Record<string, unknown> {
  const validated = LidoCsmNodeOperatorPayloadSchema.parse(payload);
  return snakeCaseTransformer(validated);
}

export function useLidoCsmApi(): UseLidoCsmApiReturn {
  const parseResponse = (
    response: AxiosResponse<ActionResult<LidoCsmNodeOperator[]>>,
  ): LidoCsmApiResult => {
    const entries = LidoCsmNodeOperatorListSchema.parse(handleResponse(response));
    return {
      entries,
      message: response.data.message ?? '',
    };
  };

  const listNodeOperators = async (): Promise<LidoCsmApiResult> => {
    const response = await api.instance.get<ActionResult<LidoCsmNodeOperator[]>>(BASE_PATH, {
      validateStatus: validWithSessionStatus,
    });

    return parseResponse(response);
  };

  const addNodeOperator = async (payload: LidoCsmNodeOperatorPayload): Promise<LidoCsmApiResult> => {
    const response = await api.instance.put<ActionResult<LidoCsmNodeOperator[]>>(
      BASE_PATH,
      toApiPayload(payload),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return parseResponse(response);
  };

  const deleteNodeOperator = async (payload: LidoCsmNodeOperatorPayload): Promise<LidoCsmApiResult> => {
    const response = await api.instance.delete<ActionResult<LidoCsmNodeOperator[]>>(BASE_PATH, {
      data: toApiPayload(payload),
      validateStatus: validStatus,
    });

    return parseResponse(response);
  };

  const refreshMetrics = async (): Promise<LidoCsmApiResult> => {
    const response = await api.instance.post<ActionResult<LidoCsmNodeOperator[]>>(
      METRICS_PATH,
      undefined,
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return parseResponse(response);
  };

  return {
    addNodeOperator,
    deleteNodeOperator,
    listNodeOperators,
    refreshMetrics,
  };
}
