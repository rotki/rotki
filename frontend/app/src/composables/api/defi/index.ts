import { handleResponse, validWithSessionAndExternalService } from '@/services/utils';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import type { ProtocolMetadata } from '@/types/defi';
import type { ActionResult } from '@rotki/common';
import type { PendingTask } from '@/types/task';

interface UseDefiApiReturn {
  fetchAirdrops: () => Promise<PendingTask>;
  fetchAirdropsMetadata: () => Promise<ProtocolMetadata[]>;
  fetchDefiMetadata: () => Promise<ProtocolMetadata[]>;
}

export function useDefiApi(): UseDefiApiReturn {
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
    fetchDefiMetadata,
  };
}
