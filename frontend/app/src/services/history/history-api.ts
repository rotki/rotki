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
import { IgnoredActions } from '@/services/history/const';
import {
  AssetMovement,
  AssetMovementCollectionResponse,
  AssetMovementRequestPayload,
  EntryWithMeta,
  EthTransaction,
  EthTransactionCollectionResponse,
  LedgerAction,
  LedgerActionCollectionResponse,
  LedgerActionRequestPayload,
  NewLedgerAction,
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

  async internalAssetMovements<T>(
    payload: AssetMovementRequestPayload,
    async: boolean
  ): Promise<T> {
    return this.axios
      .get<ActionResult<T>>('/asset_movements', {
        params: axiosSnakeCaseTransformer({
          asyncQuery: async,
          ...payload
        }),
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async assetMovementsTask(
    payload: AssetMovementRequestPayload
  ): Promise<PendingTask> {
    return this.internalAssetMovements<PendingTask>(payload, true);
  }

  async assetMovements(
    payload: AssetMovementRequestPayload
  ): Promise<CollectionResponse<EntryWithMeta<AssetMovement>>> {
    const response = await this.internalAssetMovements<
      CollectionResponse<EntryWithMeta<AssetMovement>>
    >(payload, false);

    return AssetMovementCollectionResponse.parse(response);
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

  async internalLedgerActions<T>(
    payload: LedgerActionRequestPayload,
    async: boolean
  ): Promise<T> {
    return this.axios
      .get<ActionResult<T>>('/ledgeractions', {
        params: axiosSnakeCaseTransformer({
          asyncQuery: async,
          ...payload
        }),
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      })
      .then(handleResponse);
  }

  async ledgerActionsTask(
    payload: LedgerActionRequestPayload
  ): Promise<PendingTask> {
    return this.internalLedgerActions<PendingTask>(payload, true);
  }

  async ledgerActions(
    payload: LedgerActionRequestPayload
  ): Promise<CollectionResponse<EntryWithMeta<LedgerAction>>> {
    const response = await this.internalLedgerActions<
      CollectionResponse<EntryWithMeta<LedgerAction>>
    >(payload, false);

    return LedgerActionCollectionResponse.parse(response);
  }

  async addLedgerAction(ledgerAction: NewLedgerAction): Promise<LedgerAction> {
    return this.axios
      .put<ActionResult<LedgerAction>>(
        '/ledgeractions',
        axiosSnakeCaseTransformer(ledgerAction),
        {
          validateStatus: validStatus,
          transformResponse: basicAxiosTransformer,
          transformRequest: this.requestTransformer
        }
      )
      .then(handleResponse);
  }

  async editLedgerAction(ledgerAction: LedgerAction): Promise<LedgerAction> {
    return this.axios
      .patch<ActionResult<LedgerAction>>(
        '/ledgeractions',
        { action: ledgerAction },
        {
          validateStatus: validStatus,
          transformResponse: basicAxiosTransformer,
          transformRequest: this.requestTransformer
        }
      )
      .then(handleResponse);
  }

  async deleteLedgerAction(identifier: number): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/ledgeractions', {
        data: axiosSnakeCaseTransformer({ identifier }),
        validateStatus: validStatus
      })
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
