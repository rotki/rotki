import { AxiosInstance, AxiosTransformer } from 'axios';
import {
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import { balanceKeys, basicAxiosTransformer } from '@/services/consts';
import { tradeNumericKeys } from '@/services/history/const';
import {
  LedgerActionResult,
  NewTrade,
  Trade,
  TradeLocation
} from '@/services/history/types';
import {
  ActionResult,
  EntryWithMeta,
  LimitedResponse,
  PendingTask
} from '@/services/types-api';
import {
  handleResponse,
  validStatus,
  validWithParamsSessionAndExternalService
} from '@/services/utils';
import { LedgerAction } from '@/store/history/types';
import { assert } from '@/utils/assertions';

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
        transformResponse: setupTransformer()
      })
      .then(handleResponse);
  }

  async ethTransactions(address: string): Promise<PendingTask> {
    assert(address.length > 0);
    return this.axios
      .get<ActionResult<PendingTask>>(
        `/blockchains/ETH/transactions/${address}`,
        {
          params: axiosSnakeCaseTransformer({ asyncQuery: true }),
          validateStatus: validWithParamsSessionAndExternalService,
          transformResponse: setupTransformer()
        }
      )
      .then(handleResponse);
  }

  async ledgerActions(
    start: number = 0,
    end: number | undefined = undefined,
    location: string | undefined = undefined
  ): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>(`/ledgeractions`, {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          fromTimestamp: start,
          toTimestamp: end ? end : undefined,
          location: location ? location : undefined
        }),
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async addLedgerAction(
    action: Omit<LedgerAction, 'identifier'>
  ): Promise<LedgerActionResult> {
    return this.axios
      .put<ActionResult<LedgerActionResult>>(
        '/ledgeractions',
        axiosSnakeCaseTransformer(action),
        {
          validateStatus: validStatus,
          transformResponse: setupTransformer(balanceKeys)
        }
      )
      .then(handleResponse);
  }

  async editLedgerAction(
    action: LedgerAction
  ): Promise<LimitedResponse<EntryWithMeta<LedgerAction>>> {
    return this.axios
      .patch<ActionResult<LimitedResponse<EntryWithMeta<LedgerAction>>>>(
        '/ledgeractions',
        axiosSnakeCaseTransformer({ action }),
        {
          validateStatus: validStatus,
          transformResponse: setupTransformer(balanceKeys)
        }
      )
      .then(handleResponse);
  }

  async deleteLedgerAction(
    identifier: number
  ): Promise<LimitedResponse<EntryWithMeta<LedgerAction>>> {
    return this.axios
      .delete<ActionResult<LimitedResponse<EntryWithMeta<LedgerAction>>>>(
        '/ledgeractions',
        {
          data: axiosSnakeCaseTransformer({ identifier }),
          validateStatus: validStatus,
          transformResponse: setupTransformer(balanceKeys)
        }
      )
      .then(handleResponse);
  }
}
