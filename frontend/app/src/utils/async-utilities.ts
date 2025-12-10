import { startPromise } from '@shared/utils';
import { logger } from '@/utils/logging';

interface WaitForConditionOptions {
  timeout?: number;
  interval?: number;
  initialDelay?: number;
  name: string;
  signal?: AbortSignal;
}

class AsyncUtilityError extends Error {
  constructor(message: string, public code: string, public cause?: Error) {
    super(message);
    this.name = 'AsyncUtilityError';
  }
}

class TimeoutError extends AsyncUtilityError {
  constructor(operation: string, timeout: number, cause?: Error) {
    super(`Timeout waiting for ${operation} (${timeout}ms)`, 'TIMEOUT', cause);
    this.name = 'TimeoutError';
  }
}

class AbortedError extends AsyncUtilityError {
  constructor(operation: string, cause?: Error) {
    super(`Operation ${operation} was aborted`, 'ABORTED', cause);
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
    const timeoutId = setTimeout(() => {
      abortController.abort();
      reject(new TimeoutError(name, timeout));
    }, timeout);

    let isCompleted = false;

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
