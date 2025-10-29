import type { ActionResult } from '@rotki/common';
import type { PendingTask } from '@/types/task';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';

interface GnosisPaySiweApiReturn {
  fetchGnosisPayAdmins: () => Promise<Record<string, string[]>>;
  fetchNonce: () => Promise<PendingTask>;
  verifySiweSignature: (message: string, signature: string) => Promise<PendingTask>;
}

export function useGnosisPaySiweApi(): GnosisPaySiweApiReturn {
  const fetchGnosisPayAdmins = async (): Promise<Record<string, string[]>> => {
    const response = await api.instance.get<ActionResult<Record<string, string[]>>>(
      '/services/gnosispay/admins',
    );

    return handleResponse(response);
  };

  const fetchNonce = async (): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(
      '/services/gnosispay/nonce',
      {
        params: snakeCaseTransformer({ asyncQuery: true }),
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const verifySiweSignature = async (
    message: string,
    signature: string,
  ): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      '/services/gnosispay/token',
      snakeCaseTransformer({
        asyncQuery: true,
        message,
        signature,
      }),
      {
        validateStatus: validStatus,
      },
    );
    return handleResponse(response);
  };

  return {
    fetchGnosisPayAdmins,
    fetchNonce,
    verifySiweSignature,
  };
}
