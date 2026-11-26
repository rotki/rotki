import type { TablePaginationData } from '@rotki/ui-library';
import type { Schema } from 'zod';
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import type { Sorting } from '@/modules/core/table/pagination-filter-types';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { computed, type ComputedRef, type MaybeRefOrGetter, toValue, watch } from 'vue';
import { watchDebounced } from '@/modules/core/common/async/scoped-timers';
import { getApiSortingParams } from '@/modules/core/table/pagination-filter-utils';
import { mergeParams, type ParamSource, transformFilters } from '@/modules/core/table/param-sources';
import { behaviourKeysFromFields, routeSchemaFromFields } from '@/modules/core/table/route';

interface UseTableRequestPayloadOptions<TSort extends NonNullable<unknown>, TFilter extends MatchedKeywordWithBehaviour<string> | void> {
  /** The pill-bar fields; they decide the behaviour-wrapped keys and the route filter schema. */
  fields: MaybeRefOrGetter<FieldDef[] | undefined>;
  /** The filter bag merged into the payload. */
  filters: MaybeRefOrGetter<TFilter>;
  /** External parameter sources; only those reaching the request are merged. */
  params: ParamSource[];
  /** The raw page/limit state the offset is computed from. */
  internalPagination: MaybeRefOrGetter<TablePaginationData>;
  /** The raw sorting state sent to the API. */
  internalSorting: MaybeRefOrGetter<Sorting<TSort>>;
  /** The sorting used when `internalSorting` names no column. */
  defaultSorting: () => Sorting<TSort>;
  /** Milliseconds to coalesce rapid payload changes into one handler call. `0` calls it on every change. */
  debounce: number;
}

interface UseTableRequestPayloadReturn<TPayload> {
  /** The assembled request payload. */
  requestPayload: ComputedRef<TPayload>;
  /** The route filter schema read off the fields, or `undefined` when the table declares none. */
  routeFilterSchema: () => Schema | undefined;
  /** Watches `requestPayload`, debounced when the table asked for it. */
  watchRequestPayload: (handler: (payload: TPayload, oldPayload: TPayload) => Promise<void>) => void;
}

/**
 * Assembles the request payload of a server table from its filter bag, param sources,
 * pagination and sorting, and owns the field-derived shape of that payload.
 */
export function useTableRequestPayload<
  TSort extends NonNullable<unknown>,
  TPayload,
  TFilter extends MatchedKeywordWithBehaviour<string> | void,
>(options: UseTableRequestPayloadOptions<TSort, TFilter>): UseTableRequestPayloadReturn<TPayload> {
  const { debounce, defaultSorting, fields, filters, internalPagination, internalSorting, params } = options;

  // Recomputed rather than captured: a gated field list can change while the table is mounted.
  const behaviourKeys = computed<string[]>(() => behaviourKeysFromFields(toValue(fields) ?? []));
  const routeFilterSchema = computed<Schema | undefined>(() => {
    const declared = toValue(fields);
    return declared ? routeSchemaFromFields(declared) : undefined;
  });

  const requestPayload = computed<TPayload>(() => {
    const { limit, page } = toValue(internalPagination);
    const offset = (page - 1) * limit;

    const merged = mergeParams(params, 'request', toValue(filters) ?? {});
    const transformed = transformFilters(merged, toValue(behaviourKeys));

    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- only the caller's payload type describes its filter bag plus its param sources
    return {
      ...transformed,
      limit,
      offset,
      ...getApiSortingParams(toValue(internalSorting), defaultSorting()),
    } as TPayload;
  });

  const watchRequestPayload = (handler: (payload: TPayload, oldPayload: TPayload) => Promise<void>): void => {
    if (debounce > 0) {
      watchDebounced(requestPayload, handler, { debounce });
    }
    else {
      watch(requestPayload, handler);
    }
  };

  return {
    requestPayload,
    routeFilterSchema: (): Schema | undefined => toValue(routeFilterSchema),
    watchRequestPayload,
  };
}
