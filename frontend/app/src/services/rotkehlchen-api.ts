import axios, { type AxiosInstance } from 'axios';
import { basicAxiosTransformer } from '@/services/axios-tranformers';

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
}

export const api = new RotkehlchenApi();
