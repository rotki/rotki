import { UserCancelledTaskError } from '@/types/task';

export function isOfEnum<T extends { [s: string]: unknown }>(e: T) {
  return (token: any): token is T[keyof T] => Object.values(e).includes(token as T[keyof T]);
}

export function isTaskCancelled(error: any): boolean {
  return error instanceof UserCancelledTaskError;
}
