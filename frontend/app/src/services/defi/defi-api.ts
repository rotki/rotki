import { AxiosInstance } from 'axios';
import { ActionResult, AsyncQuery } from '@/services/types-api';
import {
  validWithSessionAndExternalService,
  handleResponse
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
          validateStatus: validWithSessionAndExternalService,
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
          validateStatus: validWithSessionAndExternalService,
          params: {
            async_query: true
          }
        }
      )
      .then(handleResponse);
  }

  async fetchAaveBalances(): Promise<AsyncQuery> {
    return this.axios
      .get<ActionResult<AsyncQuery>>('/blockchains/ETH/modules/aave/balances', {
        validateStatus: validWithSessionAndExternalService,
        params: {
          async_query: true
        }
      })
      .then(handleResponse);
  }

  async fetchAaveHistory(reset?: boolean): Promise<AsyncQuery> {
    return this.axios
      .get<ActionResult<AsyncQuery>>('/blockchains/ETH/modules/aave/history', {
        validateStatus: validWithSessionAndExternalService,
        params: {
          async_query: true,
          reset_db_data: reset
        }
      })
      .then(handleResponse);
  }

  async fetchAllDefi(): Promise<AsyncQuery> {
    return this.axios
      .get<ActionResult<AsyncQuery>>('/blockchains/ETH/defi', {
        validateStatus: validWithSessionAndExternalService,
        params: {
          async_query: true
        }
      })
      .then(handleResponse);
  }
}
