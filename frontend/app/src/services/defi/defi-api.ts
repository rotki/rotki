import { AxiosInstance, AxiosTransformer } from 'axios';
import {
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import { ActionResult, PendingTask } from '@/services/types-api';
import {
  validWithSessionAndExternalService,
  handleResponse
} from '@/services/utils';

export class DefiApi {
  private readonly axios: AxiosInstance;
  private readonly baseTransformer: AxiosTransformer[];

  constructor(axios: AxiosInstance) {
    this.axios = axios;
    this.baseTransformer = setupTransformer();
  }

  async dsrBalance(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>(
        'blockchains/ETH/modules/makerdao/dsrbalance',
        {
          params: axiosSnakeCaseTransformer({
            asyncQuery: true
          }),
          validateStatus: validWithSessionAndExternalService,
          transformResponse: this.baseTransformer
        }
      )
      .then(handleResponse);
  }

  async dsrHistory(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>(
        'blockchains/ETH/modules/makerdao/dsrhistory',
        {
          params: axiosSnakeCaseTransformer({
            asyncQuery: true
          }),
          validateStatus: validWithSessionAndExternalService,
          transformResponse: this.baseTransformer
        }
      )
      .then(handleResponse);
  }

  async makerDAOVaults(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>(
        'blockchains/ETH/modules/makerdao/vaults',
        {
          validateStatus: validWithSessionAndExternalService,
          params: axiosSnakeCaseTransformer({
            asyncQuery: true
          }),
          transformResponse: this.baseTransformer
        }
      )
      .then(handleResponse);
  }

  async makerDAOVaultDetails(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>(
        '/blockchains/ETH/modules/makerdao/vaultdetails',
        {
          validateStatus: validWithSessionAndExternalService,
          params: axiosSnakeCaseTransformer({
            asyncQuery: true
          }),
          transformResponse: this.baseTransformer
        }
      )
      .then(handleResponse);
  }

  async fetchAaveBalances(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>(
        '/blockchains/ETH/modules/aave/balances',
        {
          validateStatus: validWithSessionAndExternalService,
          params: axiosSnakeCaseTransformer({
            asyncQuery: true
          }),
          transformResponse: this.baseTransformer
        }
      )
      .then(handleResponse);
  }

  async fetchAaveHistory(reset?: boolean): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>('/blockchains/ETH/modules/aave/history', {
        validateStatus: validWithSessionAndExternalService,
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          resetDbData: reset
        }),
        transformResponse: this.baseTransformer
      })
      .then(handleResponse);
  }

  async fetchAllDefi(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>('/blockchains/ETH/defi', {
        validateStatus: validWithSessionAndExternalService,
        params: axiosSnakeCaseTransformer({
          asyncQuery: true
        }),
        transformResponse: this.baseTransformer
      })
      .then(handleResponse);
  }

  async fetchCompoundBalances(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>(
        '/blockchains/ETH/modules/compound/balances',
        {
          validateStatus: validWithSessionAndExternalService,
          params: axiosSnakeCaseTransformer({ asyncQuery: true }),
          transformResponse: this.baseTransformer
        }
      )
      .then(handleResponse);
  }

  async fetchCompoundHistory(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>(
        '/blockchains/ETH/modules/compound/history',
        {
          validateStatus: validWithSessionAndExternalService,
          params: axiosSnakeCaseTransformer({ asyncQuery: true }),
          transformResponse: this.baseTransformer
        }
      )
      .then(handleResponse);
  }

  async fetchYearnVaultsHistory(reset?: boolean): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>(
        '/blockchains/ETH/modules/yearn/vaults/history',
        {
          validateStatus: validWithSessionAndExternalService,
          params: axiosSnakeCaseTransformer({
            asyncQuery: true,
            resetDbData: reset
          }),
          transformResponse: this.baseTransformer
        }
      )
      .then(handleResponse);
  }
}
