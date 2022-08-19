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
  EthDetectedTokensRecord,
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
import {
  EthAddressBookLocation,
  EthNames,
  EthNamesEntries
} from '@/store/balances/types';
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

  async addManualBalances(
    balances: Omit<ManualBalance, 'id'>[]
  ): Promise<ManualBalances> {
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

  async deleteManualBalances(ids: number[]): Promise<ManualBalances> {
    return this.axios
      .delete<ActionResult<ManualBalances>>('balances/manual', {
        data: { ids },
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

  async internalEnsNames<T>(
    ethereumAddresses: string[],
    asyncQuery: boolean = false
  ): Promise<T> {
    return this.axios
      .post<ActionResult<T>>(
        '/names/ens/reverse',
        axiosSnakeCaseTransformer({
          ethereumAddresses,
          asyncQuery,
          ignoreCache: asyncQuery
        }),
        {
          validateStatus: validWithSessionAndExternalService,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async getEnsNamesTask(ethAddresses: string[]): Promise<PendingTask> {
    return this.internalEnsNames<PendingTask>(ethAddresses, true);
  }

  async getEnsNames(ethAddresses: string[]): Promise<EthNames> {
    const response = await this.internalEnsNames<EthNames>(ethAddresses);

    return EthNames.parse(response);
  }

  async getEthAddressBook(
    location: EthAddressBookLocation,
    addresses?: string[]
  ): Promise<EthNamesEntries> {
    const response = await this.axios.post<ActionResult<EthNames>>(
      `/names/addressbook/${location}`,
      addresses ? { addresses } : null,
      {
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );

    return EthNamesEntries.parse(handleResponse(response));
  }

  async addEthAddressBook(
    location: EthAddressBookLocation,
    entries: EthNamesEntries
  ): Promise<boolean> {
    return await this.axios
      .put<ActionResult<boolean>>(
        `/names/addressbook/${location}`,
        { entries },
        {
          validateStatus: validWithSessionAndExternalService,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async updateEthAddressBook(
    location: EthAddressBookLocation,
    entries: EthNamesEntries
  ): Promise<boolean> {
    return this.axios
      .patch<ActionResult<boolean>>(
        `/names/addressbook/${location}`,
        { entries },
        {
          validateStatus: validWithSessionAndExternalService,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async deleteEthAddressBook(
    location: EthAddressBookLocation,
    addresses: string[]
  ): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>(`/names/addressbook/${location}`, {
        data: axiosSnakeCaseTransformer({ addresses }),
        validateStatus: validWithSessionAndExternalService
      })
      .then(handleResponse);
  }

  async getEthNames(addresses: string[]): Promise<EthNames> {
    return this.axios
      .post<ActionResult<EthNames>>(
        '/names',
        { addresses },
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

  async internalDetectedTokens<T>(
    addresses: string[],
    asyncQuery: boolean
  ): Promise<T> {
    return this.axios
      .post<ActionResult<T>>(
        '/blockchains/ETH/tokens/detect',
        axiosSnakeCaseTransformer({
          asyncQuery,
          onlyCache: !asyncQuery,
          addresses
        }),
        {
          validateStatus: validWithParamsSessionAndExternalService,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async fetchDetectedTokensTask(addresses: string[]): Promise<PendingTask> {
    return this.internalDetectedTokens<PendingTask>(addresses, true);
  }

  async fetchDetectedTokens(
    addresses: string[]
  ): Promise<EthDetectedTokensRecord> {
    const response = await this.internalDetectedTokens<EthDetectedTokensRecord>(
      addresses,
      false
    );

    return EthDetectedTokensRecord.parse(response);
  }
}
