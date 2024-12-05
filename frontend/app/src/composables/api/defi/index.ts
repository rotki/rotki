import { fetchExternalAsync, handleResponse, validWithSessionAndExternalService } from '@/services/utils';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import type { ProtocolMetadata } from '@/types/defi';
import type { ActionResult } from '@rotki/common';
import type { PendingTask } from '@/types/task';

interface UseDefiApiReturn {
  fetchAllDefi: () => Promise<PendingTask>;
  fetchAirdrops: () => Promise<PendingTask>;
  fetchAirdropsMetadata: () => Promise<ProtocolMetadata[]>;
  fetchDefiMetadata: () => Promise<ProtocolMetadata[]>;
}

export function useDefiApi(): UseDefiApiReturn {
  const fetchAllDefi = async (): Promise<PendingTask> => fetchExternalAsync(api.instance, '/blockchains/eth/defi');

  const fetchAirdrops = async (): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>('/blockchains/eth/airdrops', {
      params: snakeCaseTransformer({
        asyncQuery: true,
      }),
      validateStatus: validWithSessionAndExternalService,
    });

    return handleResponse(response);
  };

  const fetchAirdropsMetadata = async (): Promise<ProtocolMetadata[]> => {
    const response = await api.instance.get<ActionResult<ProtocolMetadata[]>>('/airdrops/metadata');

    return handleResponse(response);
  };

  const fetchDefiMetadata = async (): Promise<ProtocolMetadata[]> => {
    const response = await api.instance.get<ActionResult<ProtocolMetadata[]>>('/defi/metadata');
    return handleResponse(response);
  };

  return {
    fetchAirdrops,
    fetchAirdropsMetadata,
    fetchAllDefi,
    fetchDefiMetadata,
  };
}
