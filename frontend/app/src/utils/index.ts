import { UserCancelledTaskError } from '@/types/task';

export const startPromise = <T>(promise: Promise<T>): void => {
  promise.then().catch(e => logger.debug(e));
};

export const isOfEnum =
  <T extends { [s: string]: unknown }>(e: T) =>
  (token: any): token is T[keyof T] =>
    Object.values(e).includes(token as T[keyof T]);

export const isTaskCancelled = (error: any) =>
  error instanceof UserCancelledTaskError;
