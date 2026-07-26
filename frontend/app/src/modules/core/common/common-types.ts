import type { Ref } from 'vue';

/**
 * A composable parameter that must stay a writable `Ref`, because something other than the
 * composable itself writes to it (a callee, or the caller through a `v-model`). Identical to
 * `Ref<T>`; the distinct name documents the contract and tells
 * `@rotki/composable-input-flexibility` not to suggest `MaybeRefOrGetter<T>`, which cannot be
 * written to. Do NOT use it merely to silence the rule: if the ref is only read, widen it instead.
 */
export type WritableRef<T> = Ref<T>;

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

export type ConflictResolutionStrategy = 'remote' | 'local';

export interface SelectOption<T = string> {
  key: T;
  label?: string;
}

export type SelectOptions<T = string> = SelectOption<T>[];
