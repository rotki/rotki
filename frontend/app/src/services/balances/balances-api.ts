import { Nullable } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { ActionResult } from '@rotki/common/lib/data';
import {
  Eth2ValidatorEntry,
  Eth2Validators
} from '@rotki/common/lib/staking/eth2';
import { AxiosInstance } from 'axios';
import {
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import {
  ManualBalance,
  ManualBalances,
  OracleCacheMeta
} from '@/services/balances/types';
import {
  balanceAxiosTransformer,
  basicAxiosTransformer
} from '@/services/consts';
import { ApiImplementation, PendingTask } from '@/services/types-api';
import {
  fetchExternalAsync,
  handleResponse,
  validStatus,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService,
  validWithSessionStatus
} from '@/services/utils';
import { EnsNames } from '@/store/balances/types';
import { Eth2Validator } from '@/types/balances';
import { SupportedExchange } from '@/types/exchanges';
import { Module } from '@/types/modules';
import { PriceOracle } from '@/types/user';

export class BalancesApi {
  private readonly axios: AxiosInstance;

  constructor(axios: AxiosInstance) {
    this.axios = axios;
  }

  private get api(): ApiImplementation {
    return {
      axios: this.axios,
      baseTransformer: setupTransformer()
    };
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

  deleteModuleData(module: Nullable<Module> = null): Promise<boolean> {
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
        axiosSnakeCaseTransformer({ balances }),
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
        axiosSnakeCaseTransformer({ balances }),
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

  async getEnsNames(
    forceUpdate: boolean = false,
    ethereumAddresses: string[]
  ): Promise<EnsNames> {
    return this.axios
      .post<ActionResult<EnsNames>>(
        '/ens/reverse',
        axiosSnakeCaseTransformer({
          forceUpdate,
          ethereumAddresses
        }),
        {
          validateStatus: validWithSessionAndExternalService,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async prices(
    assets: string[],
    targetAsset: string,
    ignoreCache: boolean
  ): Promise<PendingTask> {
    return this.axios
      .post<ActionResult<PendingTask>>(
        '/assets/prices/current',
        axiosSnakeCaseTransformer({
          asyncQuery: true,
          assets: assets.join(','),
          targetAsset,
          ignoreCache: ignoreCache ? ignoreCache : undefined
        }),
        {
          validateStatus: validWithSessionAndExternalService,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async createPriceCache(
    source: PriceOracle,
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
    source: PriceOracle,
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

  async getPriceCache(source: PriceOracle): Promise<OracleCacheMeta[]> {
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

  async fetchNfBalances(payload?: {
    ignoreCache: boolean;
  }): Promise<PendingTask> {
    const url = '/nfts/balances';
    let params = undefined;
    if (payload) {
      params = axiosSnakeCaseTransformer(payload);
    }
    return fetchExternalAsync(this.api, url, params);
  }

  async addEth2Validator(payload: Eth2Validator): Promise<PendingTask> {
    const response = await this.axios.put<ActionResult<PendingTask>>(
      '/blockchains/ETH2/validators',
      axiosSnakeCaseTransformer({ ...payload, asyncQuery: true }),
      {
        transformResponse: basicAxiosTransformer,
        validateStatus: validWithSessionAndExternalService
      }
    );

    return handleResponse(response);
  }

  async getEth2Validators(): Promise<Eth2Validators> {
    const response = await this.axios.get<ActionResult<Eth2Validators>>(
      '/blockchains/ETH2/validators',
      {
        transformResponse: basicAxiosTransformer,
        validateStatus: validWithSessionStatus
      }
    );
    const result = handleResponse(response);
    return Eth2Validators.parse(result);
  }

  async deleteEth2Validators(
    validators: Eth2ValidatorEntry[]
  ): Promise<boolean> {
    const response = await this.axios.delete<ActionResult<boolean>>(
      '/blockchains/ETH2/validators',
      {
        data: axiosSnakeCaseTransformer({
          validators
        }),
        transformResponse: basicAxiosTransformer,
        validateStatus: validWithSessionStatus
      }
    );
    return handleResponse(response);
  }

  async editEth2Validator({
    ownershipPercentage,
    validatorIndex
  }: Eth2Validator) {
    const response = await this.axios.patch<ActionResult<boolean>>(
      '/blockchains/ETH2/validators',
      axiosSnakeCaseTransformer({ ownershipPercentage, validatorIndex }),
      {
        transformResponse: basicAxiosTransformer,
        validateStatus: validWithSessionAndExternalService
      }
    );

    return handleResponse(response);
  }
}
