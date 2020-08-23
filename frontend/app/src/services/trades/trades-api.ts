import { AxiosInstance, AxiosTransformer } from 'axios';
import { ActionResult } from '@/model/action-result';
import {
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import { NewTrade, Trade, TradeLocation } from '@/services/trades/types';
import { handleResponse, validStatus } from '@/services/utils';

export class TradesApi {
  private readonly axios: AxiosInstance;
  private readonly responseTransformer: AxiosTransformer[] = setupTransformer([
    'fee',
    'amount',
    'rate'
  ]);
  private readonly requestTransformer: AxiosTransformer[];

  constructor(axios: AxiosInstance) {
    this.axios = axios;
    this.requestTransformer = [axiosSnakeCaseTransformer].concat(
      axios.defaults.transformRequest as AxiosTransformer[]
    );
  }

  async trades(location?: TradeLocation): Promise<Trade[]> {
    return this.axios
      .get<ActionResult<Trade[]>>('/trades', {
        data: location ? { data: location } : undefined,
        validateStatus: validStatus,
        transformResponse: this.responseTransformer
      })
      .then(handleResponse);
  }

  async externalTrades(): Promise<Trade[]> {
    return this.axios
      .get<ActionResult<Trade[]>>('/trades', {
        data: { location: 'external' },
        validateStatus: validStatus,
        transformResponse: this.responseTransformer
      })
      .then(handleResponse);
  }

  async addExternalTrade(trade: NewTrade): Promise<Trade> {
    return this.axios
      .put<ActionResult<Trade>>('/trades', trade, {
        validateStatus: validStatus,
        transformResponse: this.responseTransformer,
        transformRequest: this.requestTransformer
      })
      .then(handleResponse);
  }

  async editExternalTrade(trade: Trade): Promise<Trade> {
    return this.axios
      .patch<ActionResult<Trade>>('/trades', trade, {
        validateStatus: validStatus,
        transformResponse: this.responseTransformer,
        transformRequest: this.requestTransformer
      })
      .then(handleResponse);
  }

  async deleteExternalTrade(tradeId: string): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/trades', {
        data: { trade_id: tradeId },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }
}
