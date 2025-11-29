import type { ActionResult } from '@rotki/common';
import { FetchError, type FetchOptions, ofetch, type ResponseType } from 'ofetch';
import { defaultApiUrls } from '@/modules/api/api-urls';
import { DEFAULT_TIMEOUT } from '@/modules/api/constants';
import {
  camelCaseTransformer,
  noRootCamelCaseTransformer,
  queryTransformer,
  snakeCaseTransformer,
} from '@/modules/api/transformers';
import { VALID_STATUS_CODES, type ValidStatuses } from '@/modules/api/utils';
import { type RetryOptions, withRetry } from '@/modules/api/with-retry';
import { ApiValidationError } from '@/types/api/errors';
import { HTTPStatus } from '@/types/api/http';
import { nonEmptyProperties } from '@/utils/data';

interface NonEmptyPropertiesOptions {
  /** Keys to always include even if value is empty */
  alwaysPickKeys?: string[];
  /** Whether to remove empty strings as well */
  removeEmptyString?: boolean;
}

type OmittedFetchKeys = 'onRequest' | 'onResponse' | 'onResponseError' | 'retry';

export interface RotkiFetchOptions<R extends ResponseType = 'json', T = unknown>
  extends Omit<FetchOptions<R>, OmittedFetchKeys> {
  /** Skip camelCase transformation on response (returns raw JSON) */
  skipCamelCase?: boolean;
  /** Use noRootCamelCaseTransformer instead of camelCaseTransformer (skips root keys transformation) */
  skipRootCamelCase?: boolean;
  /** Skip snake_case transformation on request body/query */
  skipSnakeCase?: boolean;
  /** Valid HTTP status codes. Defaults to [200, 400, 409]. 401 is always handled separately. */
  validStatuses?: ValidStatuses;
  /** Skip automatic ActionResult unwrapping - returns raw response instead of result */
  skipResultUnwrap?: boolean;
  /** Default value to return when result is falsy instead of throwing an error */
  defaultValue?: T;
  /** Treat 409 Conflict as success, returning true. Used for logout/disconnect operations where 409 means "already done". */
  treat409AsSuccess?: boolean;
  /**
   * Filter out empty/null/undefined properties from request body before sending.
   * - `true`: Apply nonEmptyProperties with default options
   * - `{ alwaysPickKeys, removeEmptyString }`: Apply with custom options
   */
  filterEmptyProperties?: true | NonEmptyPropertiesOptions;
  /**
   * Enable retry logic for timeout/abort errors. Disabled by default.
   * - `true`: Enable with default options (maxRetries: 2, retryDelay: 20000ms)
   * - `RetryOptions`: Enable with custom configuration
   * - `false` or `undefined`: Disabled (default)
   *
   * When enabled, the request will be retried on timeout or abort errors with
   * exponential backoff (delay multiplied by retry attempt number).
   */
  retry?: boolean | RetryOptions;
}

export class RotkiApi {
  private _serverUrl: string;
  private _baseURL: string;
  private abortController: AbortController;
  private authFailureAction?: () => void;

  constructor() {
    this._serverUrl = defaultApiUrls.coreApiUrl;
    this._baseURL = `${this._serverUrl}/api/1/`;
    this.abortController = new AbortController();
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

  /**
   * Builds a full URL with query parameters.
   * Useful for generating download links.
   */
  buildUrl(path: string, query?: Record<string, unknown>): string {
    const url = new URL(path, this._baseURL);
    if (query) {
      const transformedQuery = queryTransformer(query);
      for (const [key, value] of Object.entries(transformedQuery)) {
        if (value !== null && value !== undefined) {
          url.searchParams.set(key, String(value));
        }
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

  /**
   * Handles 401 authentication failure by cancelling requests and redirecting.
   */
  private handleAuthFailure(): void {
    this.cancel();
    this.authFailureAction?.();
    window.location.href = '/#/';
  }

  /**
   * Transforms request body: filters empty properties and converts to snake_case.
   */
  private transformBody(
    body: BodyInit | Record<string, unknown> | null | undefined,
    options: { skipSnakeCase?: boolean; filterEmptyProperties?: true | NonEmptyPropertiesOptions },
  ): BodyInit | Record<string, unknown> | null | undefined {
    if (!body || body instanceof FormData)
      return body;

    let transformed = body as Record<string, unknown>;

    if (options.filterEmptyProperties) {
      const filterOptions = options.filterEmptyProperties === true ? {} : options.filterEmptyProperties;
      transformed = nonEmptyProperties(transformed, filterOptions);
    }

    if (!options.skipSnakeCase) {
      transformed = snakeCaseTransformer(transformed);
    }

    return transformed;
  }

  /**
   * Transforms query parameters: filters empty properties and converts to snake_case.
   */
  private transformQuery(
    query: Record<string, unknown> | undefined,
    options: { skipSnakeCase?: boolean; filterEmptyProperties?: true | NonEmptyPropertiesOptions },
  ): Record<string, string | number | boolean> | undefined {
    if (!query)
      return undefined;

    let transformed = query;

    if (options.filterEmptyProperties) {
      const filterOptions = options.filterEmptyProperties === true ? {} : options.filterEmptyProperties;
      transformed = nonEmptyProperties(transformed, filterOptions);
    }

    if (!options.skipSnakeCase) {
      return queryTransformer(transformed);
    }

    return transformed as Record<string, string | number | boolean>;
  }

  /**
   * Creates a response parser function based on transformation options.
   */
  private createResponseParser(
    options: { skipCamelCase?: boolean; skipRootCamelCase?: boolean },
  ): (text: string) => unknown {
    if (options.skipCamelCase)
      return (text: string) => JSON.parse(text);
    if (options.skipRootCamelCase)
      return (text: string) => noRootCamelCaseTransformer(JSON.parse(text));
    return (text: string) => camelCaseTransformer(JSON.parse(text));
  }

  /**
   * Creates and throws a FetchError with status information.
   */
  private throwStatusError(status: number, message?: string, data?: unknown): never {
    const error = new FetchError(message || `Request failed with status ${status}`);
    error.status = status;
    error.statusCode = status;
    error.data = data;
    throw error;
  }

  /**
   * Safely parses JSON text, returning null on parse failure.
   */
  private tryParseJson<T>(text: string): T | null {
    try {
      return JSON.parse(text) as T;
    }
    catch {
      return null;
    }
  }

  async fetch<T>(url: string, options: RotkiFetchOptions<'json', T> = {}): Promise<T> {
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
      ...fetchOptions
    } = options;

    const doFetch = async (): Promise<T> => {
      const body = this.transformBody(fetchOptions.body, { skipSnakeCase, filterEmptyProperties });
      const query = this.transformQuery(fetchOptions.query as Record<string, unknown> | undefined, { skipSnakeCase, filterEmptyProperties });

      const response = await ofetch.raw<ActionResult<T>>(url, {
        ...fetchOptions,
        baseURL: fetchOptions.baseURL ?? this._baseURL,
        timeout: fetchOptions.timeout ?? DEFAULT_TIMEOUT,
        signal: this.abortController.signal,
        ignoreResponseError: true,
        body,
        query,
        parseResponse: this.createResponseParser({ skipCamelCase, skipRootCamelCase }),
      });

      const status = response.status;

      if (status === HTTPStatus.UNAUTHORIZED)
        this.handleAuthFailure();

      const allowedStatuses = validStatuses ?? VALID_STATUS_CODES;
      if (!allowedStatuses.includes(status)) {
        const responseData = response._data;
        this.throwStatusError(status, responseData?.message, responseData);
      }

      const data = response._data;

      // Handle 409 Conflict as success when requested (used for logout/disconnect operations)
      if (treat409AsSuccess && status === HTTPStatus.CONFLICT)
        return true as unknown as T;

      // Skip ActionResult unwrapping if requested (for special cases like blob responses)
      if (skipResultUnwrap)
        return data as unknown as T;

      // Unwrap ActionResult: extract result or throw error with message
      const { result, message } = data as ActionResult<T>;

      // Determine if this is an error condition:
      // - null/undefined result is always an error
      // - falsy result (false, 0, '') with a non-empty message is also an error
      //   (backend returns false + message to indicate logical failure)
      // - falsy result with empty/no message is a valid response
      const isError = result === null || result === undefined || (!result && message);

      if (!isError)
        return result;

      // If defaultValue is provided, return it instead of throwing for error results
      if (defaultValue !== undefined)
        return defaultValue;

      // Throw appropriate error based on status
      if (status === HTTPStatus.BAD_REQUEST)
        throw new ApiValidationError(message);

      throw new Error(message);
    };

    // Apply retry logic if enabled
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

  /**
   * Performs a HEAD request and returns the HTTP status code.
   * Useful for checking resource existence without fetching the body.
   */
  async headStatus(
    url: string,
    options: Omit<RotkiFetchOptions, 'method' | 'retry'> = {},
  ): Promise<number> {
    const { validStatuses, skipSnakeCase, ...fetchOptions } = options;

    const query = this.transformQuery(fetchOptions.query as Record<string, unknown> | undefined, { skipSnakeCase });

    const response = await ofetch.raw(url, {
      ...fetchOptions,
      method: 'HEAD',
      baseURL: fetchOptions.baseURL ?? this._baseURL,
      timeout: fetchOptions.timeout ?? DEFAULT_TIMEOUT,
      signal: this.abortController.signal,
      ignoreResponseError: true,
      query,
    });

    const status = response.status;

    if (status === HTTPStatus.UNAUTHORIZED)
      this.handleAuthFailure();

    const allowedStatuses = validStatuses ?? VALID_STATUS_CODES;
    if (!allowedStatuses.includes(status))
      this.throwStatusError(status);

    return status;
  }

  /** Fetches a blob response for file downloads. Handles JSON error responses. */
  async fetchBlob(
    url: string,
    options: Omit<RotkiFetchOptions, 'skipCamelCase' | 'skipRootCamelCase' | 'skipResultUnwrap'> = {},
  ): Promise<Blob> {
    const { validStatuses, skipSnakeCase, ...fetchOptions } = options;

    const body = this.transformBody(fetchOptions.body, { skipSnakeCase });
    const query = this.transformQuery(fetchOptions.query as Record<string, unknown> | undefined, { skipSnakeCase });

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

    // Check if response is JSON (error case) or actual blob (success case)
    // JSON errors come back as application/json content type
    const contentType = response.headers.get('content-type');
    const isJsonError = contentType?.includes('application/json');

    if (isJsonError) {
      // Parse the blob as JSON to get the error message
      const text = await blob.text();
      const json = this.tryParseJson<ActionResult<unknown>>(text);
      if (json) {
        throw new Error(json.message || `Request failed with status ${status}`);
      }
      throw new TypeError(`Request failed with status ${status}`);
    }

    const allowedStatuses = validStatuses ?? VALID_STATUS_CODES;
    if (!allowedStatuses.includes(status))
      throw new Error(`Request failed with status ${status}`);

    return blob;
  }
}

export const api = new RotkiApi();
