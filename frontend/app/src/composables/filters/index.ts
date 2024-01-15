import { z } from 'zod';

export function useEmptyFilter<F extends NonNullable<unknown> | void, M>() {
  return {
    filters: ref<F>(),
    matchers: computed<M[]>(() => []),
    RouteFilterSchema: z.object({}),
    updateFilter: (_filter: F) => {},
  };
}
