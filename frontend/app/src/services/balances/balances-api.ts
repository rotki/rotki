import { Nullable } from '@rotki/common';
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
import { EthDetectedTokensRecord } from '@/services/balances/types';
import { basicAxiosTransformer } from '@/services/consts';
import { ApiImplementation, PendingTask } from '@/services/types-api';
import {
  fetchExternalAsync,
  handleResponse,
  validStatus,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService,
  validWithSessionStatus
} from '@/services/utils';
import { Eth2Validator } from '@/types/balances';
import {
  EthAddressBookLocation,
  EthNames,
  EthNamesEntries
} from '@/types/eth-names';
import { SupportedExchange } from '@/types/exchanges';
import { Module } from '@/types/modules';

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
