import { ActionResult } from '@rotki/common/lib/data';
import { AxiosInstance, AxiosRequestTransformer } from 'axios';
import {
  axiosSnakeCaseTransformer,
  getUpdatedKey
} from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { PendingTask } from '@/services/types-api';
import {
  handleResponse,
  paramsSerializer,
  validStatus,
  validWithParamsSessionAndExternalService,
  validWithSessionStatus
} from '@/services/utils';
import { CollectionResponse } from '@/types/collection';
import {
  LedgerAction,
  LedgerActionCollectionResponse,
  LedgerActionRequestPayload,
  NewLedgerAction
} from '@/types/history/ledger-actions';
import { EntryWithMeta } from '@/types/history/meta';
import {
  AssetMovement,
  AssetMovementCollectionResponse,
  AssetMovementRequestPayload
} from '@/types/history/movements';
import { TradeLocation } from '@/types/history/trade-location';
import {
  NewTrade,
  Trade,
  TradeCollectionResponse,
  TradeRequestPayload
} from '@/types/history/trades';
import {
  EthTransaction,
  EthTransactionCollectionResponse,
  NewEthTransactionEvent,
  TransactionEventRequestPayload,
  TransactionRequestPayload
} from '@/types/history/tx';
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
    asyncQuery: boolean
  ): Promise<T> {
    return this.axios
      .get<ActionResult<T>>('/trades', {
        params: axiosSnakeCaseTransformer({
          asyncQuery,
          ...payload
        }),
        paramsSerializer,
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

  async deleteExternalTrade(tradesIds: string[]): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/trades', {
        data: axiosSnakeCaseTransformer({ tradesIds }),
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  async internalAssetMovements<T>(
    payload: AssetMovementRequestPayload,
    asyncQuery: boolean
  ): Promise<T> {
    return this.axios
      .get<ActionResult<T>>('/asset_movements', {
        params: axiosSnakeCaseTransformer({
          asyncQuery,
          ...payload
        }),
        paramsSerializer,
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
    asyncQuery: boolean
  ): Promise<T> {
    let url = `/blockchains/ETH/transactions`;
    const { address, ...data } = payload;
    if (address) {
      url += `/${address}`;
    }
    return this.axios
      .get<ActionResult<T>>(url, {
        params: axiosSnakeCaseTransformer({
          asyncQuery,
          ...data,
          orderByAttributes:
            payload.orderByAttributes?.map(item =>
              getUpdatedKey(item, false)
            ) ?? []
        }),
        paramsSerializer,
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

  async fetchEthTransactionEvents(
    payload: TransactionEventRequestPayload
  ): Promise<PendingTask> {
    return this.axios
      .post<ActionResult<PendingTask>>(
        'blockchains/ETH/transactions',
        axiosSnakeCaseTransformer({
          asyncQuery: true,
          ...payload
        }),
        {
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }

  async addTransactionEvent(
    event: NewEthTransactionEvent
  ): Promise<{ identifier: number }> {
    return this.axios
      .put<ActionResult<{ identifier: number }>>('/history/events', event, {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer,
        transformRequest: this.requestTransformer
      })
      .then(handleResponse);
  }

  async editTransactionEvent(event: NewEthTransactionEvent): Promise<boolean> {
    return this.axios
      .patch<ActionResult<boolean>>('/history/events', event, {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer,
        transformRequest: this.requestTransformer
      })
      .then(handleResponse);
  }

  async deleteTransactionEvent(identifiers: number[]): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/history/events', {
        data: axiosSnakeCaseTransformer({ identifiers }),
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  async internalLedgerActions<T>(
    payload: LedgerActionRequestPayload,
    asyncQuery: boolean
  ): Promise<T> {
    return this.axios
      .get<ActionResult<T>>('/ledgeractions', {
        params: axiosSnakeCaseTransformer({
          asyncQuery,
          ...payload
        }),
        paramsSerializer,
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
        axiosSnakeCaseTransformer(ledgerAction),
        {
          validateStatus: validStatus,
          transformResponse: basicAxiosTransformer,
          transformRequest: this.requestTransformer
        }
      )
      .then(handleResponse);
  }

  async deleteLedgerAction(identifiers: number[]): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/ledgeractions', {
        data: axiosSnakeCaseTransformer({ identifiers }),
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

  fetchAvailableCounterparties(): Promise<string[]> {
    return this.axios
      .get<ActionResult<string[]>>(
        '/blockchains/ETH/modules/data/counterparties',
        {
          validateStatus: validStatus,
          transformResponse: basicAxiosTransformer
        }
      )
      .then(handleResponse);
  }
}
