export interface PaginationRequestPayload<T> {
  readonly limit: number;
  readonly offset: number;
  readonly orderByAttributes?: (keyof T)[];
  readonly ascending?: boolean[];
  readonly ignoreCache?: boolean;
  readonly onlyCache?: boolean;
}

export type ToSnakeCase<T> = T extends `${infer A}${infer B}${infer C}`
  ? [A, B, C] extends [Lowercase<A>, Exclude<Uppercase<B>, '_'>, C]
      ? `${A}_${Lowercase<B>}${ToSnakeCase<C>}`
      : `${Lowercase<A>}${ToSnakeCase<`${B}${C}`>}`
  : T extends string
    ? Lowercase<T>
    : T extends (infer A)[]
      ? ToSnakeCase<A>[]
      : T extends NonNullable<unknown>
        ? { [K in keyof T as ToSnakeCase<K>]: ToSnakeCase<T[K]> }
        : T;

export type CamelCase<S extends string> = S extends `${infer P1}_${infer P2}${infer P3}`
  ? `${Lowercase<P1>}${Uppercase<P2>}${CamelCase<P3>}`
  : Lowercase<S>;

export type ConflictResolutionStrategy = 'remote' | 'local';

export interface SelectOption<T = string> {
  key: T;
  label?: string;
}

export type SelectOptions<T = string> = SelectOption<T>[];
