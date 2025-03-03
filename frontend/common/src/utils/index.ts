export type Writeable<T> = { -readonly [P in keyof T]: T[P] };

export type Properties<TObj, TResult> = {
  [K in keyof TObj]: TObj[K] extends TResult ? K : never;
}[keyof TObj];

export type Nullable<T> = T | null;

export type SemiPartial<T, Ps extends keyof T> = Pick<T, Ps> & Partial<T>;

interface PromiseFunction {
  (): PromiseLike<void>;
}

export type Awaitable = VoidFunction | PromiseFunction;

export type MaybePromise<T> = T | Promise<T>;

export type Diff<T, U> = T extends U ? never : T;

export function onlyIfTruthy<T>(value: T): T | undefined {
  return value || undefined;
}

export type AddressIndexed<T> = Readonly<Record<string, T>>;
