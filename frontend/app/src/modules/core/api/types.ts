import type { FetchOptions, ResponseType } from 'ofetch';
import type { RequestTarget } from '@/modules/core/api/constants';
import type { ValidStatuses } from '@/modules/core/api/utils';
import type { RetryOptions } from '@/modules/core/api/with-retry';

export interface NonEmptyPropertiesOptions {
  /** Keys to always include even if value is empty */
  alwaysPickKeys?: string[];
  /** Whether to remove empty strings as well */
  removeEmptyString?: boolean;
}

/**
 * `baseURL` is omitted deliberately: the api owns url resolution, and a caller
 * that could override it is how colibri's origin used to drift from core's.
 * Address a different backend with `target` instead.
 */
type OmittedFetchKeys = 'onRequest' | 'onResponse' | 'onResponseError' | 'retry' | 'priority' | 'baseURL';

export interface RotkiFetchOptions<R extends ResponseType = 'json', T = unknown>
  extends Omit<FetchOptions<R, any>, OmittedFetchKeys> {
  /** Which backend to address. Defaults to {@link RequestTarget.CORE}. */
  target?: RequestTarget;
  /** Skip camelCase transformation on response (returns raw JSON) */
  skipCamelCase?: boolean;
  /** Use noRootCamelCaseTransformer instead of camelCaseTransformer (skips root keys transformation) */
  skipRootCamelCase?: boolean;
  /**
   * Response fields whose nested object must reach the caller exactly as the backend sent it.
   *
   * For a field that is a map (keyed by chain id, asset identifier, location) the camelCase
   * conversion has no field names to rename and rewrites the data instead: `polygon_pos` becomes
   * `polygonPos` while single-word keys like `base` are untouched, so a lookup by chain id matches
   * some entries and misses the rest. The field's own key is still converted.
   */
  skipCamelCaseKeys?: string[];
  /** Skip snake_case transformation on request body/query. Can be boolean or array of property names to skip. */
  skipSnakeCase?: boolean | string[];
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
  /**
   * Bypass the request queue and execute directly.
   * By default, all requests go through the queue for prioritization,
   * deduplication, rate limiting, and concurrency control.
   * Set to `true` for critical requests that must execute immediately.
   */
  skipQueue?: boolean;
  /** Request priority (higher = processed first). Uses RequestPriority constants. Default: NORMAL (4) */
  priority?: number;
  /** Tags for group cancellation (e.g., ['balances', 'eth']) */
  tags?: string[];
  /** Deduplicate identical pending requests */
  dedupe?: boolean;
  /** Override max queue time in ms (default: 60000) */
  maxQueueTime?: number;
  /** Override max retries for queue (default: 0, no retry) */
  queueRetries?: number;
  /** Skip the global 401 auth failure handler. Used for endpoints like password change where 401 means wrong password, not session expiry. */
  skipAuthHandler?: boolean;
}
