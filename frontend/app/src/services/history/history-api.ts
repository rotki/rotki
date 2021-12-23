import { ActionResult } from '@rotki/common/lib/data';
import {
  GitcoinGrantEventsPayload,
  GitcoinGrantReport,
  GitcoinReportPayload
} from '@rotki/common/lib/gitcoin';
import { AxiosInstance, AxiosRequestTransformer } from 'axios';
import {
  axiosSnakeCaseTransformer,
  getUpdatedKey,
  setupTransformer
} from '@/services/axios-tranformers';
import {
  balanceAxiosTransformer,
  basicAxiosTransformer
} from '@/services/consts';
import {
  IgnoredActions,
  movementAxiosTransformer
} from '@/services/history/const';
import {
  EntryWithMeta,
  EthTransaction,
  EthTransactionCollectionResponse,
  LedgerActionResult,
  NewTrade,
  Trade,
  TradeCollectionResponse,
  TradeLocation,
  TradeRequestPayload,
  TransactionRequestPayload
} from '@/services/history/types';
import { PendingTask } from '@/services/types-api';
import {
  handleResponse,
  validStatus,
  validWithParamsSessionAndExternalService,
  validWithSessionStatus
} from '@/services/utils';
import { LedgerAction } from '@/store/history/types';
import { CollectionResponse } from '@/types/collection';
import { ReportProgress } from '@/types/reports';

export class HistoryApi {
  private readonly axios: AxiosInstance;
  private readonly requestTransformer: AxiosRequestTransformer[];

  constructor(axios: AxiosInstance) {
    this.axios = axios;
    this.requestTransformer = [axiosSnakeCaseTransformer].concat(
      axios.defaults.transformRequest as AxiosRequestTransformer[]
    );
  }

  async associatedLocations(): Promise<TradeLocation[]> {
    return this.axios
      .get<ActionResult<TradeLocation[]>>('/locations/associated', {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async internalTrades<T>(
    payload: TradeRequestPayload,
    async: boolean
  ): Promise<T> {
    return this.axios
      .get<ActionResult<T>>('/trades', {
        params: axiosSnakeCaseTransformer({
          asyncQuery: async,
          ...payload
        }),
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async tradesTask(payload: TradeRequestPayload): Promise<PendingTask> {
    return this.internalTrades<PendingTask>(payload, true);
  }

  async trades(
    payload: TradeRequestPayload
  ): Promise<CollectionResponse<EntryWithMeta<Trade>>> {
    const response = await this.internalTrades<
      CollectionResponse<EntryWithMeta<Trade>>
    >(payload, false);

    return TradeCollectionResponse.parse(response);
  }

  async addExternalTrade(trade: NewTrade): Promise<Trade> {
    return this.axios
      .put<ActionResult<Trade>>('/trades', trade, {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer,
        transformRequest: this.requestTransformer
      })
      .then(handleResponse);
  }

  async editExternalTrade(trade: Trade): Promise<Trade> {
    return this.axios
      .patch<ActionResult<Trade>>('/trades', trade, {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer,
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

  async assetMovements(
    location?: TradeLocation,
    onlyCache?: boolean
  ): Promise<any> {
    const params = {
      asyncQuery: true,
      onlyCache: onlyCache ? onlyCache : undefined,
      location
    };
    return this.axios
      .get<ActionResult<PendingTask>>('/asset_movements', {
        params: axiosSnakeCaseTransformer(params),
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: movementAxiosTransformer
      })
      .then(handleResponse);
  }

  private internalEthTransactions<T>(
    payload: TransactionRequestPayload,
    async: boolean
  ): Promise<T> {
    let url = `/blockchains/ETH/transactions`;
    const { address, ...data } = payload;
    if (address) {
      url += `/${address}`;
    }
    return this.axios
      .get<ActionResult<T>>(url, {
        params: axiosSnakeCaseTransformer({
          asyncQuery: async,
          ...data,
          orderByAttribute: getUpdatedKey(payload.orderByAttribute, false)
        }),
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async ethTransactionsTask(
    payload: TransactionRequestPayload
  ): Promise<PendingTask> {
    return this.internalEthTransactions<PendingTask>(payload, true);
  }

  async ethTransactions(
    payload: TransactionRequestPayload
  ): Promise<CollectionResponse<EntryWithMeta<EthTransaction>>> {
    const response = await this.internalEthTransactions<
      CollectionResponse<EntryWithMeta<EthTransaction>>
    >(payload, false);

    return EthTransactionCollectionResponse.parse(response);
  }

  async ledgerActions(
    start: number = 0,
    end: number | undefined = undefined,
    location: string | undefined = undefined,
    onlyCache?: boolean
  ): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>(`/ledgeractions`, {
        params: axiosSnakeCaseTransformer({
          asyncQuery: true,
          fromTimestamp: start,
          toTimestamp: end ? end : undefined,
          location: location ? location : undefined,
          onlyCache: onlyCache ? onlyCache : undefined
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
          transformResponse: balanceAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async editLedgerAction(
    action: LedgerAction
  ): Promise<CollectionResponse<EntryWithMeta<LedgerAction>>> {
    return this.axios
      .patch<ActionResult<CollectionResponse<EntryWithMeta<LedgerAction>>>>(
        '/ledgeractions',
        axiosSnakeCaseTransformer({ action }),
        {
          validateStatus: validStatus,
          transformResponse: balanceAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async deleteLedgerAction(
    identifier: number
  ): Promise<CollectionResponse<EntryWithMeta<LedgerAction>>> {
    return this.axios
      .delete<ActionResult<CollectionResponse<EntryWithMeta<LedgerAction>>>>(
        '/ledgeractions',
        {
          data: axiosSnakeCaseTransformer({ identifier }),
          validateStatus: validStatus,
          transformResponse: balanceAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async getProgress(): Promise<ReportProgress> {
    const response = await this.axios.get<ActionResult<ReportProgress>>(
      `/history/status`,
      {
        validateStatus: validWithSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );
    const data = handleResponse(response);
    return ReportProgress.parse(data);
  }

  async gatherGitcoinGrandEvents(
    payload: GitcoinGrantEventsPayload
  ): Promise<PendingTask> {
    return this.axios
      .post<ActionResult<PendingTask>>(
        '/gitcoin/events',
        axiosSnakeCaseTransformer({ ...payload, asyncQuery: true }),
        {
          validateStatus: validStatus,
          transformResponse: balanceAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async deleteGitcoinGrantEvents(grantId: number): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/gitcoin/events', {
        data: axiosSnakeCaseTransformer({ grantId }),
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  async generateReport(
    payload: GitcoinReportPayload
  ): Promise<GitcoinGrantReport> {
    return this.axios
      .put<ActionResult<GitcoinGrantReport>>('/gitcoin/report', payload, {
        validateStatus: validStatus,
        transformResponse: setupTransformer(['total', 'amount', 'value']),
        transformRequest: this.requestTransformer
      })
      .then(handleResponse);
  }

  fetchIgnored(): Promise<IgnoredActions> {
    return this.axios
      .get<ActionResult<IgnoredActions>>('/actions/ignored', {
        validateStatus: validStatus,
        transformResponse: setupTransformer([])
      })
      .then(handleResponse)
      .then(result => IgnoredActions.parse(result));
  }
}
