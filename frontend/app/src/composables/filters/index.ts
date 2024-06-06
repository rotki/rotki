import type { FilterSchema } from '@/composables/filter-paginate';

export function useEmptyFilter<F extends NonNullable<unknown> | void, M>(): FilterSchema<F | undefined, M> {
  return {
    filters: ref(),
    matchers: computed<M[]>(() => []),
  };
}
