import { wait } from '@shared/utils';
import { FetchError } from 'ofetch';
import { DEFAULT_MAX_RETRIES, DEFAULT_RETRY_DELAY } from '@/modules/core/api/constants';
import { isAbortError } from '@/modules/core/common/helpers/is-of-enum';

export interface RetryOptions {
  /**
   * Maximum number of retry attempts after the initial request fails.
   *
   * @defaultValue {@link DEFAULT_MAX_RETRIES}
   */
  readonly maxRetries?: number;
  /**
   * Base delay in milliseconds between retries, multiplied by the attempt number for exponential
   * backoff.
   *
   * @defaultValue {@link DEFAULT_RETRY_DELAY}
   */
  readonly retryDelay?: number;
}

/**
 * Check if an error is a timeout or abort error from fetch/ofetch.
 */
export function isTimeoutError(error: unknown): boolean {
  if (error instanceof FetchError) {
    return error.message.includes('timeout') || error.message.includes('aborted');
  }
  return isAbortError(error);
}

/**
 * Runs an async function, retrying it on timeout.
 *
 * @remarks
 * Only a timeout or abort is retried, as {@link isTimeoutError} judges it. Any other rejection
 * propagates on the first attempt.
 *
 * @param requestFn - the operation to run, typically a network request
 * @param options - see {@link RetryOptions}
 * @returns the operation's result, or a rejection once the retries are exhausted
 */
export async function withRetry<T>(requestFn: () => Promise<T>, options: RetryOptions = {}): Promise<T> {
  const {
    maxRetries = DEFAULT_MAX_RETRIES,
    retryDelay = DEFAULT_RETRY_DELAY,
  } = options;
  let retries = 0;
  while (true) {
    try {
      return await requestFn();
    }
    catch (error) {
      if (!isTimeoutError(error) || retries >= maxRetries) {
        throw error;
      }

      retries++;
      await wait(retryDelay * retries);
    }
  }
}
