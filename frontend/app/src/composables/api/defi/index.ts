import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/api/utils';
import { type ProtocolMetadata, ProtocolMetadataArraySchema } from '@/types/defi';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface UseDefiApiReturn {
  fetchAirdrops: () => Promise<PendingTask>;
  fetchAirdropsMetadata: () => Promise<ProtocolMetadata[]>;
  fetchDefiMetadata: () => Promise<ProtocolMetadata[]>;
}

export function useDefiApi(): UseDefiApiReturn {
  const fetchAirdrops = async (): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('/blockchains/eth/airdrops', {
      query: { asyncQuery: true },
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });

    return PendingTaskSchema.parse(response);
  };

  const fetchAirdropsMetadata = async (): Promise<ProtocolMetadata[]> => {
    const response = await api.get<ProtocolMetadata[]>('/airdrops/metadata');
    return ProtocolMetadataArraySchema.parse(response);
  };

  const fetchDefiMetadata = async (): Promise<ProtocolMetadata[]> => {
    const response = await api.get<ProtocolMetadata[]>('/defi/metadata');
    return ProtocolMetadataArraySchema.parse(response);
  };

  return {
    fetchAirdrops,
    fetchAirdropsMetadata,
    fetchDefiMetadata,
  };
}
