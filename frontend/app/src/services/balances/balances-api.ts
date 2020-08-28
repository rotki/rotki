import { AxiosInstance } from 'axios';
import {
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import { SupportedExchange } from '@/services/balances/types';
import { TradeLocation } from '@/services/trades/types';
import { ActionResult, PendingTask } from '@/services/types-api';
import {
  handleResponse,
  validStatus,
  validWithParamsSessionAndExternalService
} from '@/services/utils';

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

  async assetMovements(location?: TradeLocation): Promise<any> {
    const params = {
      asyncQuery: true,
      location
    };
    return this.axios
      .get<ActionResult<PendingTask>>('/asset_movements', {
        params: axiosSnakeCaseTransformer(params),
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: setupTransformer([])
      })
      .then(handleResponse);
  }
}
