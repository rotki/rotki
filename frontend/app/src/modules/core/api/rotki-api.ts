import type { ActionResult } from '@rotki/common';
import type { QueueState } from '@/modules/core/api/request-queue/types';
import type { RotkiFetchOptions } from '@/modules/core/api/types';
import { ofetch } from 'ofetch';
import { combineAbortSignals } from '@/modules/core/api/abort-signals';
import { defaultApiUrl } from '@/modules/core/api/api-urls';
import { DEFAULT_TIMEOUT, DOWNLOAD_TIMEOUT, RequestTarget } from '@/modules/core/api/constants';
import { RequestCancelledError } from '@/modules/core/api/request-queue/errors';
import { RequestQueue } from '@/modules/core/api/request-queue/queue';
import { defaultPriorityFor } from '@/modules/core/api/request-queue/request-priority';
import { transformRequestBody, transformRequestQuery } from '@/modules/core/api/request-transformers';
import { createResponseParser, createStatusError, tryParseJson } from '@/modules/core/api/response-handlers';
import { queryTransformer } from '@/modules/core/api/transformers';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { HTTPStatus } from '@/modules/core/api/types/http';
import { VALID_STATUS_CODES, type ValidStatuses } from '@/modules/core/api/utils';
import { withRetry } from '@/modules/core/api/with-retry';

export class RotkiApi {
  private _serverUrl: string;
  private _baseURL: string;
  private abortController: AbortController;
  private authFailureAction?: () => void;
  private isSessionActive?: () => boolean;
  private readonly _requestQueue: RequestQueue;
  private readonly _colibriRequestQueue: RequestQueue;
  private _stopped: boolean = false;

  constructor() {
    this._serverUrl = defaultApiUrl;
    this._baseURL = `${this._serverUrl}/api/1/`;
    this.abortController = new AbortController();
    this._requestQueue = new RequestQueue(
      async <T>(url: string, options?: Record<string, unknown>) => this.fetchDirect<T>(url, options),
    );
    this._colibriRequestQueue = new RequestQueue(
      async <T>(url: string, options?: Record<string, unknown>) => this.fetchDirect<T>(url, options),
    );
  }

  get serverUrl(): string {
    return this._serverUrl;
  }

  get baseURL(): string {
    return this._baseURL;
  }

  get colibriBaseURL(): string {
    return `${this._serverUrl}/colibri`;
  }

  get defaultBackend(): boolean {
    return this._serverUrl === defaultApiUrl;
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

  /**
   * Puts the api into a quitting state: rejects any new request, cancels
   * everything queued, and aborts in-flight direct requests. Used on app
   * shutdown so nothing keeps hitting a backend that is going down. Reset by
   * {@link setup} if the backend is later restarted.
   */
  stopRequests(): void {
    this._stopped = true;
    this.cancelAllQueued();
    this.cancel();
  }

  getQueueMetrics(): QueueState {
    return this._requestQueue.getMetrics();
  }

  getColibriQueueMetrics(): QueueState {
    return this._colibriRequestQueue.getMetrics();
  }

  private baseUrlFor(target?: RequestTarget): string {
    return target === RequestTarget.COLIBRI ? this.colibriBaseURL : this._baseURL;
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
    // A fresh backend (e.g. after a restart) can accept requests again.
    this._stopped = false;
  }

  setOnAuthFailure(action: () => void, isSessionActive?: () => boolean): void {
    this.authFailureAction = action;
    this.isSessionActive = isSessionActive;
  }

  cancel(): void {
    this.abortController.abort();
    this.abortController = new AbortController();
  }

  private handleAuthFailure(): void {
    // A 401 only means "the session ended" when there *is* an active session. While
    // logged out (e.g. on the login screen, where a deployment may gate background
    // calls) a 401 is expected and must stay local to its caller — tearing down all
    // in-flight requests here would abort an in-progress login/account creation. When
    // logged in, a 401 is a real session loss, so cancel everything and route to login.
    if (this.isSessionActive && !this.isSessionActive())
      return;

    this.cancel();
    this.authFailureAction?.();
    window.location.href = '/#/';
  }

  async fetch<T>(url: string, options: RotkiFetchOptions<'json', T> = {}): Promise<T> {
    if (this._stopped)
      throw new RequestCancelledError('Application is quitting');

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

    const queue = restOptions.target === RequestTarget.COLIBRI ? this._colibriRequestQueue : this._requestQueue;

    return queue.enqueue<T>(url, {
      ...restOptions,
      priority: priority ?? defaultPriorityFor(restOptions.method),
      tags,
      dedupe,
      maxQueueTime,
      maxRetries: queueRetries,
    });
  }

  /**
   * Rejects 401 (after running the auth-failure handler unless skipped) and any
   * status outside the allowed set, mirroring the raw fetch error handling.
   */
  private checkResponseStatus<T>(
    response: { status: number; _data?: ActionResult<T> },
    flags: { validStatuses?: ValidStatuses; skipAuthHandler?: boolean },
  ): void {
    const status = response.status;

    if (status === HTTPStatus.UNAUTHORIZED) {
      if (!flags.skipAuthHandler)
        this.handleAuthFailure();

      throw createStatusError(status, response._data?.message, response._data);
    }

    const allowedStatuses: readonly number[] = flags.validStatuses ?? VALID_STATUS_CODES;
    if (!allowedStatuses.includes(status))
      throw createStatusError(status, response._data?.message, response._data);
  }

  /**
   * Unwraps an ActionResult: returns its result, falls back to defaultValue, or
   * throws (ApiValidationError on 400, plain Error otherwise) when it is an error.
   */
  private unwrapResult<T>(data: ActionResult<T> | undefined, status: number, defaultValue?: T): T {
    if (!data)
      throw createStatusError(status);

    const { result, message } = data;
    const isError = result === null || result === undefined || (!result && message);

    if (!isError)
      return result;

    if (defaultValue !== undefined)
      return defaultValue;

    if (status === HTTPStatus.BAD_REQUEST)
      throw new ApiValidationError(message);

    throw new Error(message);
  }

  /**
   * The single sanctioned generic-boundary escape. Some options
   * (`skipResultUnwrap`, `treat409AsSuccess`) intentionally resolve to a value
   * the wrapper cannot type as `T` — the caller opted into that shape — so this
   * is the one place that asserts it, keeping the assertion contained.
   *
   * Carrying the type instead was considered and does not work here: there is no schema and no
   * caller-supplied validator at this boundary, only the caller's own declared T.
   */
  private asResult<T>(value: unknown): T {
    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- see above
    return value as T;
  }

  private async fetchDirect<T>(url: string, options: Omit<RotkiFetchOptions<'json', T>, 'skipQueue' | 'priority' | 'tags' | 'dedupe' | 'maxQueueTime' | 'queueRetries'> = {}): Promise<T> {
    const {
      target,
      validStatuses,
      skipCamelCase,
      skipCamelCaseKeys,
      skipRootCamelCase,
      skipSnakeCase,
      skipResultUnwrap,
      defaultValue,
      treat409AsSuccess,
      filterEmptyProperties,
      retry,
      skipAuthHandler,
      timeout = DEFAULT_TIMEOUT,
      ...fetchOptions
    } = options;
    const doFetch = async (): Promise<T> => {
      const body = transformRequestBody(fetchOptions.body, { skipSnakeCase, filterEmptyProperties });
      const query = transformRequestQuery(fetchOptions.query, { skipSnakeCase, filterEmptyProperties });
      const { dispose, signal } = combineAbortSignals(this.abortController.signal, fetchOptions.signal, timeout);

      const response = await ofetch.raw<ActionResult<T>>(url, {
        ...fetchOptions,
        // Resolved per execution, so a request queued before `setup()` follows the new backend.
        baseURL: this.baseUrlFor(target),
        timeout,
        signal,
        ignoreResponseError: true,
        body,
        query,
        parseResponse: createResponseParser({ camelCaseSkipKeys: skipCamelCaseKeys, skipCamelCase, skipRootCamelCase }),
      }).finally(dispose);

      this.checkResponseStatus<T>(response, { validStatuses, skipAuthHandler });

      const status = response.status;
      const data = response._data;

      if (treat409AsSuccess && status === HTTPStatus.CONFLICT)
        return this.asResult<T>(true);

      if (skipResultUnwrap)
        return this.asResult<T>(data);

      return this.unwrapResult<T>(data, status, defaultValue);
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
    if (this._stopped)
      throw new RequestCancelledError('Application is quitting');

    const { validStatuses, skipSnakeCase, query: rawQuery, target, timeout = DEFAULT_TIMEOUT } = options;
    const query = transformRequestQuery(rawQuery, { skipSnakeCase });

    const response = await ofetch.raw(url, {
      method: 'HEAD',
      baseURL: this.baseUrlFor(target),
      timeout,
      signal: combineAbortSignals(this.abortController.signal, undefined, timeout).signal,
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
    if (this._stopped)
      throw new RequestCancelledError('Application is quitting');

    const { validStatuses, skipSnakeCase, target, timeout = DOWNLOAD_TIMEOUT, ...fetchOptions } = options;
    const body = transformRequestBody(fetchOptions.body, { skipSnakeCase });
    const query = transformRequestQuery(fetchOptions.query, { skipSnakeCase });

    const response = await ofetch.raw<Blob, 'blob'>(url, {
      method: fetchOptions.method,
      baseURL: this.baseUrlFor(target),
      timeout,
      signal: combineAbortSignals(this.abortController.signal, fetchOptions.signal, timeout).signal,
      responseType: 'blob',
      ignoreResponseError: true,
      body,
      query,
    });

    const blob = response._data;
    if (!blob)
      throw createStatusError(response.status);

    await this.assertBlobSuccess(response, blob, validStatuses);
    return blob;
  }

  /**
   * Validates a blob response: runs the auth-failure handler on 401, surfaces a
   * JSON error payload as an Error (or TypeError when it cannot be parsed), and
   * rejects any status outside the allowed set.
   */
  private async assertBlobSuccess(
    response: { status: number; headers: Headers },
    blob: Blob,
    validStatuses?: ValidStatuses,
  ): Promise<void> {
    const status = response.status;

    if (status === HTTPStatus.UNAUTHORIZED)
      this.handleAuthFailure();

    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      const text = await blob.text();
      const json = tryParseJson<ActionResult<unknown>>(text);
      if (json)
        throw new Error(json.message || `Request failed with status ${status}`);
      throw new TypeError(`Request failed with status ${status}`);
    }

    const allowedStatuses: readonly number[] = validStatuses ?? VALID_STATUS_CODES;
    if (!allowedStatuses.includes(status))
      throw new Error(`Request failed with status ${status}`);
  }
}

export const api = new RotkiApi();
