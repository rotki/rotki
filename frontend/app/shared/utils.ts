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

export async function backoff<T>(retries: number, call: BackoffCall<T>, delay = 5000): Promise<T> {
  let result: T;
  try {
    result = await call();
  }
  catch (error) {
    if (retries > 1) {
      await wait(delay);
      result = await backoff(retries - 1, call, delay * 2);
    }
    else {
      throw error;
    }
  }
  return result;
}
