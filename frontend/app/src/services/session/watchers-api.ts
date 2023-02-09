import { type ActionResult } from '@rotki/common/lib/data';
import { api } from '@/services/rotkehlchen-api';
import { type Watcher, Watchers } from '@/services/session/types';
import {
  handleResponse,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService
} from '@/services/utils';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';

export const useWatchersApi = () => {
  const watchers = async (): Promise<Watchers> => {
    const response = await api.instance.get<ActionResult<Watchers>>(
      '/watchers',
      {
        validateStatus: validWithSessionAndExternalService
      }
    );

    return Watchers.parse(handleResponse(response));
  };

  const addWatcher = async (
    watchers: Omit<Watcher, 'identifier'>[]
  ): Promise<Watchers> => {
    const response = await api.instance.put<ActionResult<Watchers>>(
      '/watchers',
      axiosSnakeCaseTransformer({ watchers }),
      {
        validateStatus: validWithParamsSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const editWatcher = async (watchers: Watchers): Promise<Watchers> => {
    const response = await api.instance.patch<ActionResult<Watchers>>(
      '/watchers',
      axiosSnakeCaseTransformer({ watchers }),
      {
        validateStatus: validWithParamsSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const deleteWatcher = async (identifiers: string[]): Promise<Watchers> => {
    const response = await api.instance.delete<ActionResult<Watchers>>(
      '/watchers',
      {
        data: axiosSnakeCaseTransformer({ watchers: identifiers }),
        validateStatus: validWithParamsSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  return {
    watchers,
    addWatcher,
    editWatcher,
    deleteWatcher
  };
};
