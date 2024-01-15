import { UserCancelledTaskError } from '@/types/task';

export function startPromise<T>(promise: Promise<T>): void {
  promise.then().catch(error => logger.debug(error));
}

export function isOfEnum<T extends { [s: string]: unknown }>(e: T) {
  return (token: any): token is T[keyof T] =>
    Object.values(e).includes(token as T[keyof T]);
}

export function isTaskCancelled(error: any) {
  return error instanceof UserCancelledTaskError;
}
