import { AxiosInstance } from 'axios';
import { ActionResult, AsyncQuery } from '@/model/action-result';
import { Watcher, WatcherTypes } from '@/services/defi/types';
import {
  fetchWithExternalService,
  handleResponse,
  modifyWithExternalService
} from '@/services/utils';

export class DefiApi {
  private readonly axios: AxiosInstance;

  constructor(axios: AxiosInstance) {
    this.axios = axios;
  }

  async dsrBalance(): Promise<AsyncQuery> {
    return this.axios
      .get<ActionResult<AsyncQuery>>(
        'blockchains/ETH/modules/makerdao/dsrbalance',
        {
          params: {
            async_query: true
          },
          validateStatus: function (status: number) {
            return status === 200 || status === 409 || status == 502;
          }
        }
      )
      .then(handleResponse);
  }

  async dsrHistory(): Promise<AsyncQuery> {
    return this.axios
      .get<ActionResult<AsyncQuery>>(
        'blockchains/ETH/modules/makerdao/dsrhistory',
        {
          params: {
            async_query: true
          },
          validateStatus: function (status: number) {
            return status === 200 || status === 409 || status == 502;
          }
        }
      )
      .then(handleResponse);
  }

  async makerDAOVaults(): Promise<AsyncQuery> {
    return this.axios
      .get<ActionResult<AsyncQuery>>(
        'blockchains/ETH/modules/makerdao/vaults',
        {
          validateStatus: fetchWithExternalService,
          params: {
            async_query: true
          }
        }
      )
      .then(handleResponse);
  }

  async makerDAOVaultDetails(): Promise<AsyncQuery> {
    return this.axios
      .get<ActionResult<AsyncQuery>>(
        '/blockchains/ETH/modules/makerdao/vaultdetails',
        {
          validateStatus: fetchWithExternalService,
          params: {
            async_query: true
          }
        }
      )
      .then(handleResponse);
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
