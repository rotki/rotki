import { api } from '@/modules/api/rotki-api';
import { type GnosisPayAdminsMapping, GnosisPayAdminsMappingSchema } from '@/modules/external-services/gnosis-pay/types';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface GnosisPaySiweApiReturn {
  fetchGnosisPayAdmins: () => Promise<GnosisPayAdminsMapping>;
  fetchNonce: () => Promise<PendingTask>;
  verifySiweSignature: (message: string, signature: string) => Promise<PendingTask>;
}

export function useGnosisPaySiweApi(): GnosisPaySiweApiReturn {
  const fetchGnosisPayAdmins = async (): Promise<GnosisPayAdminsMapping> => {
    const response = await api.get<GnosisPayAdminsMapping>('/services/gnosispay/admins');
    return GnosisPayAdminsMappingSchema.parse(response);
  };

  const fetchNonce = async (): Promise<PendingTask> => {
    const response = await api.get<PendingTask>(
      '/services/gnosispay/nonce',
      {
        query: { asyncQuery: true },
      },
    );

    return PendingTaskSchema.parse(response);
  };

  const verifySiweSignature = async (
    message: string,
    signature: string,
  ): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      '/services/gnosispay/token',
      {
        asyncQuery: true,
        message,
        signature,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  return {
    fetchGnosisPayAdmins,
    fetchNonce,
    verifySiweSignature,
  };
}
