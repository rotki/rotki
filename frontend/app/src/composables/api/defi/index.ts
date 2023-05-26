import { type ActionResult } from '@rotki/common/lib/data';
import {
  fetchExternalAsync,
  handleResponse,
  validWithSessionAndExternalService
} from '@/services/utils';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { type PendingTask } from '@/types/task';

export const useDefiApi = () => {
  const fetchAllDefi = async (): Promise<PendingTask> =>
    fetchExternalAsync(api.instance, '/blockchains/eth/defi');

  const fetchAirdrops = async (): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(
      '/blockchains/eth/airdrops',
      {
        params: snakeCaseTransformer({
          asyncQuery: true
        }),
        validateStatus: validWithSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  return {
    fetchAllDefi,
    fetchAirdrops
  };
};
