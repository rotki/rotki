import { AxiosInstance } from 'axios';
import { SupportedExchange } from '@/services/balances/types';
import { ActionResult } from '@/services/types-api';
import { handleResponse, validStatus } from '@/services/utils';

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
}
