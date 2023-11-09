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

export const RESOLVE_REMOTE = 'remote';

export const RESOLVE_LOCAL = 'local';

export const CONFLICT_RESOLUTION = [RESOLVE_REMOTE, RESOLVE_LOCAL] as const;

export type ConflictResolutionStrategy = (typeof CONFLICT_RESOLUTION)[number];
