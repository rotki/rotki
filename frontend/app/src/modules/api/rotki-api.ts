import type { ActionResult } from '@rotki/common';
import type { RotkiFetchOptions } from '@/modules/api/types';
import { ofetch } from 'ofetch';
import { defaultApiUrls } from '@/modules/api/api-urls';
import { DEFAULT_TIMEOUT } from '@/modules/api/constants';
import { type QueueState, RequestPriority, RequestQueue } from '@/modules/api/request-queue';
import { transformRequestBody, transformRequestQuery } from '@/modules/api/request-transformers';
import { createResponseParser, createStatusError, tryParseJson } from '@/modules/api/response-handlers';
import { queryTransformer } from '@/modules/api/transformers';
import { VALID_STATUS_CODES } from '@/modules/api/utils';
import { withRetry } from '@/modules/api/with-retry';
import { ApiValidationError } from '@/types/api/errors';
import { HTTPStatus } from '@/types/api/http';

export class RotkiApi {
  private _serverUrl: string;
  private _baseURL: string;
  private abortController: AbortController;
  private authFailureAction?: () => void;
  private _requestQueue: RequestQueue;
  private _colibriRequestQueue: RequestQueue;

  constructor() {
    this._serverUrl = defaultApiUrls.coreApiUrl;
    this._baseURL = `${this._serverUrl}/api/1/`;
    this.abortController = new AbortController();
    this._requestQueue = new RequestQueue(
      async <T>(url: string, options?: Record<string, unknown>) => this.fetchDirect<T>(url, options as Omit<RotkiFetchOptions<'json', T>, 'skipQueue' | 'priority' | 'tags' | 'dedupe' | 'maxQueueTime' | 'queueRetries'>),
    );
    this._colibriRequestQueue = new RequestQueue(
      async <T>(url: string, options?: Record<string, unknown>) => this.fetchDirect<T>(url, options as Omit<RotkiFetchOptions<'json', T>, 'skipQueue' | 'priority' | 'tags' | 'dedupe' | 'maxQueueTime' | 'queueRetries'>),
    );
  }

  get serverUrl(): string {
    return this._serverUrl;
  }

  get baseURL(): string {
    return this._baseURL;
  }

  get defaultBackend(): boolean {
    return this._serverUrl === defaultApiUrls.coreApiUrl;
  }

  get queueState(): QueueState {
    return this._requestQueue.state;
  }

  get colibriQueueState(): QueueState {
    return this._colibriRequestQueue.state;
  }

  cancelByTag(tag: string): void {
    this._requestQueue.cancelByTag(tag);
    this._colibriRequestQueue.cancelByTag(tag);
  }

  cancelAllQueued(): void {
    this._requestQueue.cancelAll();
    this._colibriRequestQueue.cancelAll();
  }

  getQueueMetrics(): QueueState {
    return this._requestQueue.getMetrics();
  }

  getColibriQueueMetrics(): QueueState {
    return this._colibriRequestQueue.getMetrics();
  }

  private isColibriRequest(baseURL?: string): boolean {
    if (!baseURL)
      return false;
    const colibriUrl = defaultApiUrls.colibriApiUrl;
    return colibriUrl !== '' && baseURL.startsWith(colibriUrl);
  }

  buildUrl(path: string, query?: Record<string, unknown>): string {
    const base = /^https?:\/\//.test(this._baseURL) ? this._baseURL : `${window.location.origin}${this._baseURL}`;
    const url = new URL(path, base);
    if (query) {
      const transformedQuery = queryTransformer(query);
      for (const [key, value] of Object.entries(transformedQuery)) {
        if (value !== null && value !== undefined)
          url.searchParams.set(key, String(value));
      }
    }
    return url.toString();
  }

  setup(serverUrl: string): void {
    this._serverUrl = serverUrl;
    this._baseURL = `${serverUrl}/api/1/`;
    this.abortController = new AbortController();
  }

  setOnAuthFailure(action: () => void): void {
    this.authFailureAction = action;
  }

  cancel(): void {
    this.abortController.abort();
    this.abortController = new AbortController();
  }

  private handleAuthFailure(): void {
    this.cancel();
    this.authFailureAction?.();
    window.location.href = '/#/';
  }

  async fetch<T>(url: string, options: RotkiFetchOptions<'json', T> = {}): Promise<T> {
    const {
      skipQueue,
      priority,
      tags,
      dedupe,
      maxQueueTime,
      queueRetries,
      ...restOptions
    } = options;

    if (skipQueue)
      return this.fetchDirect<T>(url, restOptions);

    const queue = this.isColibriRequest(restOptions.baseURL)
      ? this._colibriRequestQueue
      : this._requestQueue;

    return queue.enqueue<T>(url, {
      ...restOptions as Record<string, unknown>,
      priority: priority ?? RequestPriority.NORMAL,
      tags,
      dedupe,
      maxQueueTime,
      maxRetries: queueRetries,
    });
  }

  private async fetchDirect<T>(url: string, options: Omit<RotkiFetchOptions<'json', T>, 'skipQueue' | 'priority' | 'tags' | 'dedupe' | 'maxQueueTime' | 'queueRetries'> = {}): Promise<T> {
    const {
      validStatuses,
      skipCamelCase,
      skipRootCamelCase,
      skipSnakeCase,
      skipResultUnwrap,
      defaultValue,
      treat409AsSuccess,
      filterEmptyProperties,
      retry,
      skipAuthHandler,
      ...fetchOptions
    } = options;

    const doFetch = async (): Promise<T> => {
      const body = transformRequestBody(fetchOptions.body, { skipSnakeCase, filterEmptyProperties });
      const query = transformRequestQuery(fetchOptions.query as Record<string, unknown> | undefined, { skipSnakeCase, filterEmptyProperties });

      const response = await ofetch.raw<ActionResult<T>>(url, {
        ...fetchOptions,
        baseURL: fetchOptions.baseURL ?? this._baseURL,
        timeout: fetchOptions.timeout ?? DEFAULT_TIMEOUT,
        signal: this.abortController.signal,
        ignoreResponseError: true,
        body,
        query,
        parseResponse: createResponseParser({ skipCamelCase, skipRootCamelCase }),
      });

      const status = response.status;

      if (status === HTTPStatus.UNAUTHORIZED) {
        if (!skipAuthHandler)
          this.handleAuthFailure();

        const responseData = response._data;
        throw createStatusError(status, responseData?.message, responseData);
      }

      const allowedStatuses = validStatuses ?? VALID_STATUS_CODES;
      if (!allowedStatuses.includes(status)) {
        const responseData = response._data;
        throw createStatusError(status, responseData?.message, responseData);
      }

      const data = response._data;

      if (treat409AsSuccess && status === HTTPStatus.CONFLICT)
        return true as unknown as T;

      if (skipResultUnwrap)
        return data as unknown as T;

      const { result, message } = data as ActionResult<T>;
      const isError = result === null || result === undefined || (!result && message);

      if (!isError)
        return result;

      if (defaultValue !== undefined)
        return defaultValue;

      if (status === HTTPStatus.BAD_REQUEST)
        throw new ApiValidationError(message);

      throw new Error(message);
    };

    if (retry) {
      const retryOptions = typeof retry === 'boolean' ? {} : retry;
      return withRetry(doFetch, retryOptions);
    }

    return doFetch();
  }

  async get<T>(url: string, options?: RotkiFetchOptions<'json', T>): Promise<T> {
    return this.fetch<T>(url, { ...options, method: 'GET' });
  }

  async post<T>(url: string, body?: BodyInit | Record<string, any> | null, options?: RotkiFetchOptions<'json', T>): Promise<T> {
    return this.fetch<T>(url, { ...options, method: 'POST', body });
  }

  async put<T>(url: string, body?: BodyInit | Record<string, any> | null, options?: RotkiFetchOptions<'json', T>): Promise<T> {
    return this.fetch<T>(url, { ...options, method: 'PUT', body });
  }

  async patch<T>(url: string, body?: BodyInit | Record<string, any> | null, options?: RotkiFetchOptions<'json', T>): Promise<T> {
    return this.fetch<T>(url, { ...options, method: 'PATCH', body });
  }

  async delete<T>(url: string, options?: RotkiFetchOptions<'json', T>): Promise<T> {
    return this.fetch<T>(url, { ...options, method: 'DELETE' });
  }

  async headStatus(
    url: string,
    options: Omit<RotkiFetchOptions, 'method' | 'retry'> = {},
  ): Promise<number> {
    const { validStatuses, skipSnakeCase, query: rawQuery, baseURL, timeout } = options;
    const query = transformRequestQuery(rawQuery as Record<string, unknown> | undefined, { skipSnakeCase });

    const response = await ofetch.raw(url, {
      method: 'HEAD',
      baseURL: baseURL ?? this._baseURL,
      timeout: timeout ?? DEFAULT_TIMEOUT,
      signal: this.abortController.signal,
      ignoreResponseError: true,
      query,
    });

    const status = response.status;

    if (status === HTTPStatus.UNAUTHORIZED)
      this.handleAuthFailure();

    const allowedStatuses = validStatuses ?? VALID_STATUS_CODES;
    if (!allowedStatuses.includes(status))
      throw createStatusError(status);

    return status;
  }

  async fetchBlob(
    url: string,
    options: Omit<RotkiFetchOptions, 'skipCamelCase' | 'skipRootCamelCase' | 'skipResultUnwrap'> = {},
  ): Promise<Blob> {
    const { validStatuses, skipSnakeCase, ...fetchOptions } = options;
    const body = transformRequestBody(fetchOptions.body, { skipSnakeCase });
    const query = transformRequestQuery(fetchOptions.query as Record<string, unknown> | undefined, { skipSnakeCase });

    const response = await ofetch.raw(url, {
      method: fetchOptions.method,
      baseURL: fetchOptions.baseURL ?? this._baseURL,
      timeout: fetchOptions.timeout ?? DEFAULT_TIMEOUT,
      signal: this.abortController.signal,
      responseType: 'blob',
      ignoreResponseError: true,
      body,
      query,
    });

    const status = response.status;

    if (status === HTTPStatus.UNAUTHORIZED)
      this.handleAuthFailure();

    const blob = response._data as Blob;
    const contentType = response.headers.get('content-type');
    const isJsonError = contentType?.includes('application/json');

    if (isJsonError) {
      const text = await blob.text();
      const json = tryParseJson<ActionResult<unknown>>(text);
      if (json)
        throw new Error(json.message || `Request failed with status ${status}`);
      throw new TypeError(`Request failed with status ${status}`);
    }

    const allowedStatuses = validStatuses ?? VALID_STATUS_CODES;
    if (!allowedStatuses.includes(status))
      throw new Error(`Request failed with status ${status}`);

    return blob;
  }
}

export const api = new RotkiApi();
