import { ActionResult } from '@rotki/common/lib/data';
import { AxiosInstance } from 'axios';
import {
  QueriedAddresses,
  QueriedAddressPayload,
  Watcher,
  WatcherTypes
} from '@/services/session/types';
import {
  validWithSessionAndExternalService,
  handleResponse,
  validWithParamsSessionAndExternalService,
  validWithSessionStatus,
  validStatus
} from '@/services/utils';

export class SessionApi {
  readonly axios: AxiosInstance;

  constructor(axios: AxiosInstance) {
    this.axios = axios;
  }

  async watchers<T extends WatcherTypes>(): Promise<Watcher<T>[]> {
    return this.axios
      .get<ActionResult<Watcher<T>[]>>('/watchers', {
        validateStatus: validWithSessionAndExternalService
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
          validateStatus: validWithParamsSessionAndExternalService
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
          validateStatus: validWithParamsSessionAndExternalService
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
        validateStatus: validWithParamsSessionAndExternalService
      })
      .then(handleResponse);
  }

  async queriedAddresses(): Promise<QueriedAddresses> {
    return this.axios
      .get<ActionResult<QueriedAddresses>>('/queried_addresses', {
        validateStatus: validWithSessionStatus
      })
      .then(handleResponse);
  }

  async addQueriedAddress(
    payload: QueriedAddressPayload
  ): Promise<QueriedAddresses> {
    return this.axios
      .put<ActionResult<QueriedAddresses>>('/queried_addresses', payload, {
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  async deleteQueriedAddress(
    payload: QueriedAddressPayload
  ): Promise<QueriedAddresses> {
    return this.axios
      .delete<ActionResult<QueriedAddresses>>('/queried_addresses', {
        data: payload,
        validateStatus: validStatus
      })
      .then(handleResponse);
  }
}
