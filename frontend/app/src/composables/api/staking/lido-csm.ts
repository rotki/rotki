import type { ActionResult } from '@rotki/common';
import { api } from '@/modules/api';
import {
  VALID_STATUS_CODES,
  VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
  VALID_WITH_SESSION_STATUS,
} from '@/modules/api/utils';
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

function toApiPayload(payload: LidoCsmNodeOperatorPayload): LidoCsmNodeOperatorPayload {
  return LidoCsmNodeOperatorPayloadSchema.parse(payload);
}

export function useLidoCsmApi(): UseLidoCsmApiReturn {
  const parseResponse = (data: ActionResult<LidoCsmNodeOperator[]>): LidoCsmApiResult => {
    const entries = LidoCsmNodeOperatorListSchema.parse(data.result);
    return {
      entries,
      message: data.message ?? '',
    };
  };

  const listNodeOperators = async (): Promise<LidoCsmApiResult> => {
    const response = await api.get<ActionResult<LidoCsmNodeOperator[]>>(BASE_PATH, {
      validStatuses: VALID_WITH_SESSION_STATUS,
      skipResultUnwrap: true,
    });

    return parseResponse(response);
  };

  const addNodeOperator = async (payload: LidoCsmNodeOperatorPayload): Promise<LidoCsmApiResult> => {
    const response = await api.put<ActionResult<LidoCsmNodeOperator[]>>(BASE_PATH, toApiPayload(payload), {
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
      skipResultUnwrap: true,
    });

    return parseResponse(response);
  };

  const deleteNodeOperator = async (payload: LidoCsmNodeOperatorPayload): Promise<LidoCsmApiResult> => {
    const response = await api.delete<ActionResult<LidoCsmNodeOperator[]>>(BASE_PATH, {
      body: toApiPayload(payload),
      validStatuses: VALID_STATUS_CODES,
      skipResultUnwrap: true,
    });

    return parseResponse(response);
  };

  const refreshMetrics = async (): Promise<LidoCsmApiResult> => {
    const response = await api.post<ActionResult<LidoCsmNodeOperator[]>>(METRICS_PATH, undefined, {
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
      skipResultUnwrap: true,
    });

    return parseResponse(response);
  };

  return {
    addNodeOperator,
    deleteNodeOperator,
    listNodeOperators,
    refreshMetrics,
  };
}
