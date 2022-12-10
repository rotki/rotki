import { type ActionResult } from '@rotki/common/lib/data';
import { api } from '@/services/rotkehlchen-api';
import { type Watcher, type WatcherTypes } from '@/services/session/types';
import {
  handleResponse,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService
} from '@/services/utils';

export const useWatchersApi = () => {
  const watchers = async <T extends WatcherTypes>(): Promise<Watcher<T>[]> =>
    api.instance
      .get<ActionResult<Watcher<T>[]>>('/watchers', {
        validateStatus: validWithSessionAndExternalService
      })
      .then(handleResponse);

  const addWatcher = async <T extends WatcherTypes>(
    watchers: Omit<Watcher<T>, 'identifier'>[]
  ): Promise<Watcher<T>[]> =>
    api.instance
      .put<ActionResult<Watcher<T>[]>>(
        '/watchers',
        { watchers },
        {
          validateStatus: validWithParamsSessionAndExternalService
        }
      )
      .then(handleResponse);

  const editWatcher = async <T extends WatcherTypes>(
    watchers: Watcher<T>[]
  ): Promise<Watcher<T>[]> =>
    api.instance
      .patch<ActionResult<Watcher<T>[]>>(
        '/watchers',
        { watchers },
        {
          validateStatus: validWithParamsSessionAndExternalService
        }
      )
      .then(handleResponse);

  const deleteWatcher = async <T extends WatcherTypes>(
    identifiers: string[]
  ): Promise<Watcher<T>[]> =>
    api.instance
      .delete<ActionResult<Watcher<T>[]>>('/watchers', {
        data: { watchers: identifiers },
        validateStatus: validWithParamsSessionAndExternalService
      })
      .then(handleResponse);

  return {
    watchers,
    addWatcher,
    editWatcher,
    deleteWatcher
  };
};
