import { AxiosInstance } from 'axios';
import {
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import {
  ManualBalance,
  ManualBalances,
  SupportedExchange
} from '@/services/balances/types';
import { balanceKeys, basicAxiosTransformer } from '@/services/consts';
import { ActionResult, PendingTask } from '@/services/types-api';
import {
  handleResponse,
  validStatus,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService
} from '@/services/utils';
import { Blockchain } from '@/typing/types';

export class BalancesApi {
  private readonly axios: AxiosInstance;
  constructor(axios: AxiosInstance) {
    this.axios = axios;
  }

  deleteExchangeData(name: SupportedExchange | '' = ''): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>(`/exchanges/data/${name}`, {
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  deleteEthereumTransactions(): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>(`/blockchains/ETH/transactions`, {
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  async manualBalances(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>('balances/manual', {
        params: axiosSnakeCaseTransformer({ asyncQuery: true }),
        transformResponse: basicAxiosTransformer,
        validateStatus: validWithSessionAndExternalService
      })
      .then(handleResponse);
  }

  async addManualBalances(balances: ManualBalance[]): Promise<ManualBalances> {
    return this.axios
      .put<ActionResult<ManualBalances>>(
        'balances/manual',
        {
          balances
        },
        {
          transformResponse: setupTransformer(balanceKeys),
          validateStatus: validWithParamsSessionAndExternalService
        }
      )
      .then(handleResponse);
  }

  async editManualBalances(balances: ManualBalance[]): Promise<ManualBalances> {
    return this.axios
      .patch<ActionResult<ManualBalances>>(
        'balances/manual',
        {
          balances
        },
        {
          transformResponse: setupTransformer(balanceKeys),
          validateStatus: validWithParamsSessionAndExternalService
        }
      )
      .then(handleResponse);
  }

  async deleteManualBalances(labels: string[]): Promise<ManualBalances> {
    return this.axios
      .delete<ActionResult<ManualBalances>>('balances/manual', {
        data: { labels },
        transformResponse: setupTransformer(balanceKeys),
        validateStatus: validWithParamsSessionAndExternalService
      })
      .then(handleResponse);
  }

  async queryBlockchainBalances(
    ignoreCache: boolean = false,
    blockchain?: Blockchain
  ): Promise<PendingTask> {
    let url = '/balances/blockchains';
    if (blockchain) {
      url += `/${blockchain}`;
    }
    return this.axios
      .get<ActionResult<PendingTask>>(url, {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          ignoreCache: ignoreCache ? true : undefined
        }),
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }
}
