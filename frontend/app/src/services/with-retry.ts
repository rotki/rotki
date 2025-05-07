import { wait } from '@shared/utils';
import { isAxiosError } from 'axios';

interface WithRetryOptions {
  readonly maxRetries?: number;
  readonly retryDelay?: number;
}

function isTimeoutError(error: any): boolean {
  return isAxiosError(error) && error.code === 'ECONNABORTED';
}

/**
 * Executes a given asynchronous function with retry logic in case of timeout errors.
 *
 * @template T The generic return type of the original request.
 * @param {() => Promise<T>} requestFn - The asynchronous function to be executed, typically representing a network request or similar operation.
 * @param {WithRetryOptions} [options={}] - Optional configuration for retry behavior, including maximum retry attempts and delay between retries.
 * @param {number} [options.maxRetries=2] - The maximum number of retries to attempt in case of a timeout error.
 * @param {number} [options.retryDelay=20000] - The base delay in milliseconds between retries, which is multiplied by the retry attempt count.
 * @return {Promise<T>} - A promise that resolves to the result of the given asynchronous function or rejects with an error if retries are exceeded or a non-timeout error occurs.
 */
export async function withRetry<T>(requestFn: () => Promise<T>, options: WithRetryOptions = {}): Promise<T> {
  const {
    maxRetries = 2,
    retryDelay = 20000,
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
