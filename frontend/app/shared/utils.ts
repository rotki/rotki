export const checkIfDevelopment = (): boolean => import.meta.env.DEV;

/**
 * Generate a UUID v4 string.
 * Uses crypto.randomUUID() when available, with fallbacks for older environments.
 */
export function generateUUID(): string {
  if (typeof crypto !== 'undefined') {
    // Best case: native randomUUID
    if (typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }

    // Fallback: use crypto.getRandomValues if available
    if (typeof crypto.getRandomValues === 'function') {
      return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (crypto.getRandomValues(new Uint8Array(1))[0] & 15) >> (c === 'x' ? 0 : 2);
        return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
      });
    }
  }

  // Last resort: Math.random (not cryptographically secure, but functional)
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.trunc(Math.random() * 16);
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

export function startPromise<T>(promise: Promise<T>): void {
  promise.then().catch(error => console.error(error));
}

type BackoffCall<T> = () => Promise<T>;

export async function wait(duration: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, duration));
}

/** Waits `duration` ms, or until `signal` aborts, whichever comes first. */
async function waitUnlessAborted(duration: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const done = (): void => {
      clearTimeout(timer);
      signal.removeEventListener('abort', done);
      resolve();
    };
    const timer = setTimeout(done, duration);
    signal.addEventListener('abort', done, { once: true });
  });
}

/**
 * Calls `call`, retrying a failure up to `retries` attempts in all, doubling `delay` (ms) each time.
 *
 * @remarks
 * Once `signal` aborts, the last failure is thrown instead of retrying, including from inside a
 * wait, so a caller holding a running flag across the retries gets it back at once.
 */
export async function backoff<T>(retries: number, call: BackoffCall<T>, delay = 5000, signal?: AbortSignal): Promise<T> {
  try {
    return await call();
  }
  catch (error) {
    if (retries <= 1 || signal?.aborted)
      throw error;

    if (signal)
      await waitUnlessAborted(delay, signal);
    else
      await wait(delay);

    if (signal?.aborted)
      throw error;

    return backoff(retries - 1, call, delay * 2, signal);
  }
}
