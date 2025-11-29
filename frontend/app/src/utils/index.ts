import { UserCancelledTaskError } from '@/types/task';

export function isOfEnum<T extends { [s: string]: unknown }>(e: T) {
  return (token: any): token is T[keyof T] => Object.values(e).includes(token as T[keyof T]);
}

export function isTaskCancelled(error: any): boolean {
  return error instanceof UserCancelledTaskError;
}

/**
 * Check if an error is an abort/cancellation error from fetch/ofetch.
 * This occurs when a request is cancelled via AbortController.
 */
export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}
