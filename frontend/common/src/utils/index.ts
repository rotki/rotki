export type Writeable<T> = { -readonly [P in keyof T]: T[P] };

export type Nullable<T> = T | null;

export type SemiPartial<T, Ps extends keyof T> = Pick<T, Ps> & Partial<T>;

interface PromiseFunction {
  (): PromiseLike<void>;
}

export type Awaitable = VoidFunction | PromiseFunction;

export type MaybePromise<T> = T | Promise<T>;

export function onlyIfTruthy<T>(value: T): T | undefined {
  return value || undefined;
}
