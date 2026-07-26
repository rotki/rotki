export function isOfEnum<T extends Record<string, unknown>>(e: T) {
  return (token: unknown): token is T[keyof T] => Object.values(e).includes(token);
}

/**
 * Check if an error is an abort/cancellation error from fetch/ofetch.
 * This occurs when a request is cancelled via AbortController.
 */
export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}
