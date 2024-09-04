import axios, { type AxiosInstance } from 'axios';
import { basicAxiosTransformer } from '@/services/axios-tranformers';

export class RotkehlchenApi {
  private axios: AxiosInstance;
  private _serverUrl: string;
  private signal = axios.CancelToken.source();
  private readonly pathname: string;
  private authFailureAction?: () => void;

  get defaultServerUrl(): string {
    if (import.meta.env.VITE_BACKEND_URL)
      return import.meta.env.VITE_BACKEND_URL as string;

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
      transformResponse: basicAxiosTransformer,
    });
    this.setupCancellation();
    this.setupAuthRedirect();
  }

  setup(serverUrl: string): void {
    this._serverUrl = serverUrl;
    this.axios = axios.create({
      baseURL: `${serverUrl}/api/1/`,
      timeout: 30000,
      transformResponse: basicAxiosTransformer,
    });
    this.setupCancellation();
    this.setupAuthRedirect();
  }

  setOnAuthFailure(action: () => void): void {
    this.authFailureAction = action;
  }

  private setupCancellation(): void {
    this.axios.interceptors.request.use(
      (request) => {
        request.cancelToken = this.signal.token;
        return request;
      },
      (error) => {
        if (error.response)
          return Promise.reject(error.response.data);

        return Promise.reject(error);
      },
    );
  }

  private setupAuthRedirect(): void {
    this.axios.interceptors.response.use(
      (response) => {
        if (response.status === 401) {
          this.cancel();
          this.authFailureAction?.();
          window.location.href = '/#/';
        }

        return response;
      },
      (error) => {
        if (error.response) {
          if (error.response.status === 401) {
            this.cancel();
            window.location.href = '/#/';
          }
          return Promise.reject(error.response.data);
        }
        return Promise.reject(error);
      },
    );
  }
}

export const api = new RotkehlchenApi();
