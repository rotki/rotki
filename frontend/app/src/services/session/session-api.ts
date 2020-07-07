import { AxiosInstance } from 'axios';
import { ActionResult } from '@/model/action-result';
import { Watcher, WatcherTypes } from '@/services/session/types';
import {
  fetchWithExternalService,
  handleResponse,
  modifyWithExternalService
} from '@/services/utils';

export class SessionApi {
  readonly axios: AxiosInstance;

  constructor(axios: AxiosInstance) {
    this.axios = axios;
  }

  async watchers<T extends WatcherTypes>(): Promise<Watcher<T>[]> {
    return this.axios
      .get<ActionResult<Watcher<T>[]>>('/watchers', {
        validateStatus: fetchWithExternalService
      })
      .then(handleResponse);
  }

  async addWatcher<T extends WatcherTypes>(
    watchers: Omit<Watcher<T>, 'identifier'>[]
  ): Promise<Watcher<T>[]> {
    return this.axios
      .put<ActionResult<Watcher<T>[]>>(
        '/watchers',
        { watchers },
        {
          validateStatus: modifyWithExternalService
        }
      )
      .then(handleResponse);
  }

  async editWatcher<T extends WatcherTypes>(
    watchers: Watcher<T>[]
  ): Promise<Watcher<T>[]> {
    return this.axios
      .patch<ActionResult<Watcher<T>[]>>(
        '/watchers',
        { watchers },
        {
          validateStatus: modifyWithExternalService
        }
      )
      .then(handleResponse);
  }

  async deleteWatcher<T extends WatcherTypes>(
    identifiers: string[]
  ): Promise<Watcher<T>[]> {
    return this.axios
      .delete<ActionResult<Watcher<T>[]>>('/watchers', {
        data: { watchers: identifiers },
        validateStatus: modifyWithExternalService
      })
      .then(handleResponse);
  }
}
