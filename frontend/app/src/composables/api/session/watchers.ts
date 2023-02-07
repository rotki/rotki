import { type ActionResult } from '@rotki/common/lib/data';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService
} from '@/services/utils';
import { type Watcher, type WatcherTypes } from '@/types/session';

export const useWatchersApi = () => {
  const watchers = async <T extends WatcherTypes>(): Promise<Watcher<T>[]> => {
    const response = await api.instance.get<ActionResult<Watcher<T>[]>>(
      '/watchers',
      {
        validateStatus: validWithSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const addWatcher = async <T extends WatcherTypes>(
    watchers: Omit<Watcher<T>, 'identifier'>[]
  ): Promise<Watcher<T>[]> => {
    const response = await api.instance.put<ActionResult<Watcher<T>[]>>(
      '/watchers',
      { watchers },
      {
        validateStatus: validWithParamsSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const editWatcher = async <T extends WatcherTypes>(
    watchers: Watcher<T>[]
  ): Promise<Watcher<T>[]> => {
    const response = await api.instance.patch<ActionResult<Watcher<T>[]>>(
      '/watchers',
      { watchers },
      {
        validateStatus: validWithParamsSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const deleteWatcher = async <T extends WatcherTypes>(
    identifiers: string[]
  ): Promise<Watcher<T>[]> => {
    const response = await api.instance.delete<ActionResult<Watcher<T>[]>>(
      '/watchers',
      {
        data: { watchers: identifiers },
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
