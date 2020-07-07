import { AxiosInstance } from 'axios';
import { ActionResult, AsyncQuery } from '@/model/action-result';
import { fetchWithExternalService, handleResponse } from '@/services/utils';

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
}
