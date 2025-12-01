import { wait } from '@shared/utils';
import { FetchError } from 'ofetch';
import { DEFAULT_MAX_RETRIES, DEFAULT_RETRY_DELAY } from '@/modules/api/constants';
import { isAbortError } from '@/utils';

export interface RetryOptions {
  /**
   * Maximum number of retry attempts after the initial request fails.
   * @default DEFAULT_MAX_RETRIES (2)
   */
  readonly maxRetries?: number;
  /**
   * Base delay in milliseconds between retries. The actual delay is multiplied
   * by the retry attempt number (exponential backoff).
   * @default DEFAULT_RETRY_DELAY (20000ms)
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
 * Executes a given asynchronous function with retry logic in case of timeout errors.
 *
 * @template T The generic return type of the original request.
 * @param requestFn - The asynchronous function to be executed, typically representing a network request or similar operation.
 * @param options - Optional configuration for retry behavior, including maximum retry attempts and delay between retries.
 * @returns A promise that resolves to the result of the given asynchronous function or rejects with an error if retries are exceeded or a non-timeout error occurs.
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
