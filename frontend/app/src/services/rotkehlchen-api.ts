import { ActionResult } from '@rotki/common/lib/data';
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { AssetApi } from '@/services/assets/asset-api';
import {
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import { BalancesApi } from '@/services/balances/balances-api';
import { basicAxiosTransformer } from '@/services/consts';
import { DefiApi } from '@/services/defi/defi-api';
import { HistoryApi } from '@/services/history/history-api';
import { ReportsApi } from '@/services/reports/reports-api';
import {
  BackendInfo,
  PendingTask,
  SyncAction,
  TaskNotFoundError,
  TaskStatus
} from '@/services/types-api';
import {
  handleResponse,
  validAuthorizedStatus,
  validStatus,
  validTaskStatus,
  validWithoutSessionStatus,
  validWithParamsSessionAndExternalService
} from '@/services/utils';
import { TaskResultResponse } from '@/types/task';

export class RotkehlchenApi {
  private axios: AxiosInstance;
  private _defi: DefiApi;
  private _balances: BalancesApi;
  private _history: HistoryApi;
  private _reports: ReportsApi;
  private _assets: AssetApi;
  private _serverUrl: string;
  private signal = axios.CancelToken.source();
  private readonly pathname: string;

  get defaultServerUrl(): string {
    if (import.meta.env.VITE_BACKEND_URL) {
      return import.meta.env.VITE_BACKEND_URL as string;
    }

    if (import.meta.env.VITE_PUBLIC_PATH) {
      const pathname = this.pathname;
      return pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
    }

    return '';
  }

  get instance(): AxiosInstance {
    return this.axios;
  }

  get serverUrl(): string {
    return this._serverUrl;
  }

  get defaultBackend(): boolean {
    return this._serverUrl === this.defaultServerUrl;
  }

  public cancel() {
    this.signal.cancel('cancelling all pending requests');
    this.signal = axios.CancelToken.source();
  }

  private setupApis = (axios: AxiosInstance) => ({
    defi: new DefiApi(axios),
    balances: new BalancesApi(axios),
    history: new HistoryApi(axios),
    reports: new ReportsApi(axios),
    assets: new AssetApi(axios)
  });

  constructor() {
    this.pathname = window.location.pathname;
    this._serverUrl = this.defaultServerUrl;
    this.axios = axios.create({
      baseURL: `${this.serverUrl}/api/1/`,
      timeout: 30000
    });
    this.setupCancellation();
    ({
      defi: this._defi,
      balances: this._balances,
      history: this._history,
      reports: this._reports,
      assets: this._assets
    } = this.setupApis(this.axios));
  }

  get defi(): DefiApi {
    return this._defi;
  }

  get balances(): BalancesApi {
    return this._balances;
  }

  get history(): HistoryApi {
    return this._history;
  }

  get reports(): ReportsApi {
    return this._reports;
  }

  get assets(): AssetApi {
    return this._assets;
  }

  setup(serverUrl: string) {
    this._serverUrl = serverUrl;
    this.axios = axios.create({
      baseURL: `${serverUrl}/api/1/`,
      timeout: 30000
    });
    this.setupCancellation();
    ({
      defi: this._defi,
      balances: this._balances,
      history: this._history,
      reports: this._reports,
      assets: this._assets
    } = this.setupApis(this.axios));
  }

  private setupCancellation() {
    this.axios.interceptors.request.use(
      request => {
        request.cancelToken = this.signal.token;
        return request;
      },
      error => {
        if (error.response) {
          return Promise.reject(error.response.data);
        }
        return Promise.reject(error);
      }
    );
  }

  async setPremiumCredentials(
    username: string,
    apiKey: string,
    apiSecret: string
  ): Promise<true> {
    const response = await this.axios.patch<ActionResult<true>>(
      `/users/${username}`,
      {
        premium_api_key: apiKey,
        premium_api_secret: apiSecret
      },
      { validateStatus: validAuthorizedStatus }
    );

    return handleResponse(response);
  }

  async deletePremiumCredentials(): Promise<true> {
    const response = await this.axios.delete<ActionResult<true>>('/premium', {
      validateStatus: validStatus
    });

    return handleResponse(response);
  }

  async forceSync(action: SyncAction): Promise<PendingTask> {
    const response = await this.axios.put<ActionResult<PendingTask>>(
      '/premium/sync',
      axiosSnakeCaseTransformer({ asyncQuery: true, action }),
      {
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  }

  async ping(): Promise<PendingTask> {
    const ping = await this.axios.get<ActionResult<PendingTask>>('/ping', {
      transformResponse: basicAxiosTransformer
    }); // no validate status here since defaults work
    return handleResponse(ping);
  }

  async info(checkForUpdates: boolean = false): Promise<BackendInfo> {
    const response = await this.axios.get<ActionResult<BackendInfo>>('/info', {
      params: axiosSnakeCaseTransformer({
        checkForUpdates
      }),
      transformResponse: basicAxiosTransformer
    });
    return BackendInfo.parse(handleResponse(response));
  }

  async queryTasks(): Promise<TaskStatus> {
    const response = await this.axios.get<ActionResult<TaskStatus>>(`/tasks`, {
      validateStatus: validTaskStatus,
      transformResponse: basicAxiosTransformer
    });

    return handleResponse(response);
  }

  queryTaskResult<T>(
    id: number,
    numericKeys?: string[] | null,
    transform: boolean = true
  ): Promise<ActionResult<T>> {
    const requiresSetup = numericKeys || numericKeys === null;
    const transformer = requiresSetup
      ? setupTransformer(numericKeys)
      : this.axios.defaults.transformResponse;

    const config: Partial<AxiosRequestConfig> = {
      validateStatus: validTaskStatus
    };

    if (transform) {
      config.transformResponse = transformer;
    }

    return this.axios
      .get<ActionResult<TaskResultResponse<ActionResult<T>>>>(
        `/tasks/${id}`,
        config
      )
      .then(response => {
        if (response.status === 404) {
          throw new TaskNotFoundError(`Task with id ${id} not found`);
        }
        return response;
      })
      .then(handleResponse)
      .then(value => {
        if (value.outcome) {
          return value.outcome;
        }
        throw new Error('No result');
      });
  }

  async importDataFrom(
    source: string,
    file: string,
    timestampFormat: string | null
  ): Promise<PendingTask> {
    const response = await this.axios.put<ActionResult<PendingTask>>(
      '/import',
      axiosSnakeCaseTransformer({
        source,
        file,
        timestampFormat,
        asyncQuery: true
      }),
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  }

  async importFile(data: FormData): Promise<PendingTask> {
    const response = await this.axios.post<ActionResult<PendingTask>>(
      '/import',
      data,
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer,
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    );

    return handleResponse(response);
  }

  async queryBinanceMarkets(location: string): Promise<string[]> {
    const response = await this.axios.get<ActionResult<string[]>>(
      '/exchanges/binance/pairs',
      {
        params: axiosSnakeCaseTransformer({
          location: location
        })
      }
    );

    return handleResponse(response);
  }

  async queryBinanceUserMarkets(
    name: string,
    location: string
  ): Promise<string[]> {
    const response = await this.axios.get<ActionResult<string[]>>(
      `/exchanges/binance/pairs/${name}`,
      {
        params: axiosSnakeCaseTransformer({
          location: location
        })
      }
    );

    return handleResponse(response);
  }

  async fetchNfts(ignoreCache: boolean): Promise<PendingTask> {
    const params = Object.assign(
      {
        asyncQuery: true
      },
      ignoreCache ? { ignoreCache } : {}
    );
    const response = await this.axios.get<ActionResult<PendingTask>>('/nfts', {
      params: axiosSnakeCaseTransformer(params),
      validateStatus: validWithoutSessionStatus,
      transformResponse: basicAxiosTransformer
    });

    return handleResponse(response);
  }
}

export const api = new RotkehlchenApi();
