import { AxiosInstance } from 'axios';
import { PriceOracles } from '@/model/action-result';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import {
  ManualBalance,
  ManualBalances,
  OracleCacheMeta,
  SupportedExchange
} from '@/services/balances/types';
import {
  balanceAxiosTransformer,
  basicAxiosTransformer
} from '@/services/consts';
import { SupportedModules } from '@/services/session/types';
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

  deleteModuleData(module: SupportedModules | null = null): Promise<boolean> {
    const url = module
      ? `/blockchains/ETH/modules/${module}/data`
      : `/blockchains/ETH/modules/data`;
    return this.axios
      .delete<ActionResult<boolean>>(url, {
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
          transformResponse: balanceAxiosTransformer,
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
          transformResponse: balanceAxiosTransformer,
          validateStatus: validWithParamsSessionAndExternalService
        }
      )
      .then(handleResponse);
  }

  async deleteManualBalances(labels: string[]): Promise<ManualBalances> {
    return this.axios
      .delete<ActionResult<ManualBalances>>('balances/manual', {
        data: { labels },
        transformResponse: balanceAxiosTransformer,
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

  async prices(
    assets: string[],
    targetAsset: string,
    ignoreCache: boolean
  ): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>('/assets/prices/current', {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          assets: assets.join(','),
          targetAsset,
          ignoreCache: ignoreCache ? ignoreCache : undefined
        }),
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async createPriceCache(
    source: PriceOracles,
    fromAsset: string,
    toAsset: string,
    purgeOld: boolean = false
  ): Promise<PendingTask> {
    return this.axios
      .post<ActionResult<PendingTask>>(
        `/oracles/${source}/cache`,
        axiosSnakeCaseTransformer({
          asyncQuery: true,
          purgeOld: purgeOld ? purgeOld : undefined,
          fromAsset,
          toAsset
        }),
        {
          validateStatus: validWithSessionAndExternalService,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async deletePriceCache(
    source: PriceOracles,
    fromAsset: string,
    toAsset: string
  ): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>(`/oracles/${source}/cache`, {
        data: axiosSnakeCaseTransformer({
          fromAsset,
          toAsset
        }),
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async getPriceCache(source: PriceOracles): Promise<OracleCacheMeta[]> {
    return this.axios
      .get<ActionResult<OracleCacheMeta[]>>(`/oracles/${source}/cache`, {
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  fetchRate(
    fromAsset: string,
    toAsset: string,
    timestamp: number
  ): Promise<PendingTask> {
    return this.axios
      .post<ActionResult<PendingTask>>(
        '/assets/prices/historical',
        axiosSnakeCaseTransformer({
          asyncQuery: true,
          assetsTimestamp: [[fromAsset, timestamp]],
          targetAsset: toAsset
        }),
        {
          validateStatus: validWithSessionAndExternalService,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async loopring(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>(
        'blockchains/ETH/modules/loopring/balances',
        {
          params: axiosSnakeCaseTransformer({ asyncQuery: true }),
          validateStatus: validWithSessionAndExternalService,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }
}
