import { startPromise } from '@shared/utils';
import { logger } from '@/modules/core/common/logging/logging';

interface WaitForConditionOptions {
  timeout?: number;
  interval?: number;
  initialDelay?: number;
  name: string;
  signal?: AbortSignal;
}

class AsyncUtilityError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = 'AsyncUtilityError';
  }
}

// The code lives on each subclass rather than travelling through the constructor, so `options` can be
// forwarded to `super()` untouched and a native `cause` survives.
class TimeoutError extends AsyncUtilityError {
  readonly code = 'TIMEOUT';

  constructor(operation: string, options: ErrorOptions & { timeout: number }) {
    super(`Timeout waiting for ${operation} (${options.timeout}ms)`, options);
    this.name = 'TimeoutError';
  }
}

class AbortedError extends AsyncUtilityError {
  readonly code = 'ABORTED';

  constructor(operation: string, options?: ErrorOptions) {
    super(`Operation ${operation} was aborted`, options);
    this.name = 'AbortedError';
  }
}

export async function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new AbortedError('delay'));
      return;
    }

    const timeoutId = setTimeout(resolve, ms);

    const onAbort = (): void => {
      clearTimeout(timeoutId);
      reject(new AbortedError('delay'));
    };

    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

/**
 * Races `promise` against a timeout, rejecting with a `TimeoutError` named after `operation` if the
 * timeout wins. The timer is cleared on every exit path, so a fast promise leaves nothing pending.
 *
 * Note the loser of the race is not cancelled: this only bounds how long the caller waits.
 */
export async function withTimeout<T>(promise: Promise<T>, timeout: number, operation: string): Promise<T> {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  try {
    const timeoutPromise = new Promise<never>((_, reject) => {
      timeoutId = setTimeout(() => reject(new TimeoutError(operation, { timeout })), timeout);
    });
    return await Promise.race([promise, timeoutPromise]);
  }
  finally {
    clearTimeout(timeoutId);
  }
}

export async function waitForCondition<T>(checkFn: () => Promise<T>, condition: (result: T) => boolean, options: WaitForConditionOptions): Promise<T> {
  const {
    initialDelay = 0,
    interval = 500,
    name,
    signal,
    timeout = 30000,
  } = options;

  if (signal?.aborted) {
    throw new AbortedError(name);
  }

  const abortController = new AbortController();
  const combinedSignal = signal ? AbortSignal.any([signal, abortController.signal]) : abortController.signal;

  return new Promise((resolve, reject) => {
    let isCompleted = false;
    let timeoutId: ReturnType<typeof setTimeout>;

    /**
     * Tears the poll down, in an order that decides which rejection the caller sees.
     *
     * @remarks
     * The abort listener is removed before aborting. Aborting first fires `onAbort`, and the
     * caller observes an `AbortedError` instead of whatever the caller of this was reporting.
     */
    const cleanup = (): void => {
      isCompleted = true;
      clearTimeout(timeoutId);
      combinedSignal.removeEventListener('abort', onAbort);
      abortController.abort();
    };

    function onAbort(): void {
      if (isCompleted)
        return; // Don't reject if we're completing successfully
      cleanup();
      reject(new AbortedError(name));
    }

    timeoutId = setTimeout(() => {
      cleanup();
      reject(new TimeoutError(name, { timeout }));
    }, timeout);

    combinedSignal.addEventListener('abort', onAbort, { once: true });

    const poll = async (): Promise<void> => {
      if (combinedSignal.aborted) {
        return;
      }

      try {
        const result = await checkFn();
        if (condition(result)) {
          logger.debug(`${name} completed successfully`);
          cleanup();
          resolve(result);
        }
        else {
          logger.debug(`${name} not ready, retrying...`);
          await delay(interval, combinedSignal);
          await poll();
        }
      }
      catch (error) {
        if (combinedSignal.aborted) {
          return;
        }
        logger.debug(`${name} check failed, retrying:`, error);
        await delay(interval, combinedSignal);
        await poll();
      }
    };

    if (initialDelay > 0) {
      delay(initialDelay, combinedSignal)
        .then(async () => poll())
        .catch(() => {});
    }
    else {
      startPromise(poll());
    }
  });
}
