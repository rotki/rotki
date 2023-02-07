import { type ActionResult } from '@rotki/common/lib/data';
import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios';
import {
  axiosSnakeCaseTransformer,
  basicAxiosTransformer
} from '@/services/axios-tranformers';
import {
  BackendInfo,
  type PendingTask,
  type SyncAction,
  TaskNotFoundError,
  type TaskStatus
} from '@/services/types-api';
import {
  handleResponse,
  validAuthorizedStatus,
  validStatus,
  validTaskStatus,
  validWithParamsSessionAndExternalService,
  validWithoutSessionStatus
} from '@/services/utils';
import { SyncConflictError, SyncConflictPayload } from '@/types/login';
import { type TaskResultResponse } from '@/types/task';

export class RotkehlchenApi {
  private axios: AxiosInstance;
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

  public cancel(): void {
    this.signal.cancel('cancelling all pending requests');
    this.signal = axios.CancelToken.source();
  }

  constructor() {
    this.pathname = window.location.pathname;
    this._serverUrl = this.defaultServerUrl;
    this.axios = axios.create({
      baseURL: `${this.serverUrl}/api/1/`,
      timeout: 30000,
      transformResponse: basicAxiosTransformer
    });
    this.setupCancellation();
  }

  setup(serverUrl: string) {
    this._serverUrl = serverUrl;
    this.axios = axios.create({
      baseURL: `${serverUrl}/api/1/`,
      timeout: 30000,
      transformResponse: basicAxiosTransformer
    });
    this.setupCancellation();
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
        validateStatus: validWithParamsSessionAndExternalService
      }
    );

    return handleResponse(response);
  }

  async ping(): Promise<PendingTask> {
    const ping = await this.axios.get<ActionResult<PendingTask>>('/ping'); // no validate status here since defaults work
    return handleResponse(ping);
  }

  async info(checkForUpdates = false): Promise<BackendInfo> {
    const response = await this.axios.get<ActionResult<BackendInfo>>('/info', {
      params: axiosSnakeCaseTransformer({
        checkForUpdates
      })
    });
    return BackendInfo.parse(handleResponse(response));
  }

  async queryTasks(): Promise<TaskStatus> {
    const response = await this.axios.get<ActionResult<TaskStatus>>(`/tasks`, {
      validateStatus: validTaskStatus
    });

    return handleResponse(response);
  }

  async queryTaskResult<T>(id: number): Promise<ActionResult<T>> {
    const config: Partial<AxiosRequestConfig> = {
      validateStatus: validTaskStatus
    };

    const response = await this.axios.get<
      ActionResult<TaskResultResponse<ActionResult<T>>>
    >(`/tasks/${id}`, config);

    if (response.status === 404) {
      throw new TaskNotFoundError(`Task with id ${id} not found`);
    }

    const { outcome, statusCode } = handleResponse(response);

    if (outcome) {
      if (statusCode === 300) {
        const { result, message } = outcome;
        throw new SyncConflictError(message, SyncConflictPayload.parse(result));
      }
      return outcome;
    }

    throw new Error('No result');
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
        validateStatus: validStatus
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
        headers: {
          'Content-Type': 'multipart/form-data'
        }
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
      validateStatus: validWithoutSessionStatus
    });

    return handleResponse(response);
  }
}

export const api = new RotkehlchenApi();
