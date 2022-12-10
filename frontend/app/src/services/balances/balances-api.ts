import { type Nullable } from '@rotki/common';
import { type ActionResult } from '@rotki/common/lib/data';
import {
  type Eth2ValidatorEntry,
  Eth2Validators
} from '@rotki/common/lib/staking/eth2';
import { type AxiosInstance } from 'axios';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { EthDetectedTokensRecord } from '@/services/balances/types';
import { type PendingTask } from '@/services/types-api';
import {
  handleResponse,
  validStatus,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService,
  validWithSessionStatus
} from '@/services/utils';
import { type Eth2Validator } from '@/types/balances';
import { type SupportedExchange } from '@/types/exchanges';
import { type Module } from '@/types/modules';

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

  async addEth2Validator(payload: Eth2Validator): Promise<PendingTask> {
    const response = await this.axios.put<ActionResult<PendingTask>>(
      '/blockchains/ETH2/validators',
      axiosSnakeCaseTransformer({ ...payload, asyncQuery: true })
    );

    return handleResponse(response);
  }

  async getEth2Validators(): Promise<Eth2Validators> {
    const response = await this.axios.get<ActionResult<Eth2Validators>>(
      '/blockchains/ETH2/validators',
      {
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
        validateStatus: validWithSessionStatus
      }
    );
    return handleResponse(response);
  }

  async editEth2Validator({
    ownershipPercentage,
    validatorIndex
  }: Eth2Validator): Promise<boolean> {
    const response = await this.axios.patch<ActionResult<boolean>>(
      '/blockchains/ETH2/validators',
      axiosSnakeCaseTransformer({ ownershipPercentage, validatorIndex }),
      {
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
          validateStatus: validWithParamsSessionAndExternalService
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
