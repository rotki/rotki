export * from './account';

export * from './assets';

export * from './assertions';

export * from './balances';

export * from './blockchain';

export * from './color';

export * from './data';

export * from './defi';

export * from './history';

export * from './liquity';

export * from './messages';

export * from './numbers';

export * from './premium';

export * from './settings';

export * from './staking';

export * from './statistics';

export * from './text';

export type Writeable<T> = { -readonly [P in keyof T]: T[P] };

export type Properties<TObj, TResult> = {
  [K in keyof TObj]: TObj[K] extends TResult ? K : never;
}[keyof TObj];

export type Nullable<T> = T | null;

export type SemiPartial<T, Ps extends keyof T> = Pick<T, Ps> & Partial<T>;

export type AddressIndexed<T> = Readonly<Record<string, T>>;

interface PromiseFunction {
  (): PromiseLike<void>;
}

export type Awaitable = VoidFunction | PromiseFunction;

export type Diff<T, U> = T extends U ? never : T;

export function onlyIfTruthy<T>(value: T): T | undefined {
  return value || undefined;
}
