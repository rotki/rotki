import { AxiosInstance, AxiosTransformer } from 'axios';
import {
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import { tradeNumericKeys } from '@/services/history/const';
import { NewTrade, Trade, TradeLocation } from '@/services/history/types';
import { ActionResult, PendingTask } from '@/services/types-api';
import {
  handleResponse,
  validStatus,
  validWithParamsSessionAndExternalService
} from '@/services/utils';

export class HistoryApi {
  private readonly axios: AxiosInstance;
  private readonly responseTransformer: AxiosTransformer[] = setupTransformer(
    tradeNumericKeys
  );
  private readonly requestTransformer: AxiosTransformer[];

  constructor(axios: AxiosInstance) {
    this.axios = axios;
    this.requestTransformer = [axiosSnakeCaseTransformer].concat(
      axios.defaults.transformRequest as AxiosTransformer[]
    );
  }

  async trades(location?: TradeLocation): Promise<PendingTask> {
    const params = {
      asyncQuery: true,
      location
    };
    return this.axios
      .get<ActionResult<PendingTask>>('/trades', {
        params: axiosSnakeCaseTransformer(params),
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
        data: axiosSnakeCaseTransformer({ tradeId }),
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
