import type { DataTableSortData } from '@rotki/ui-library';
import type { ParamDestination } from '@/modules/core/table/param-sources';
import type { ChangeSource } from '@/modules/core/table/use-change-intent';
import { isEqual } from 'es-toolkit';

/**
 * The whole of a server table's synchronous state. Deliberately small: param source
 * values, transient values, the self-echo tag, and the collection total live in the
 * adapter, not here (see the Stage 3 design spec). This keeps `reduce` a pure
 * function testable with no router, no timers, no mounted component.
 */
export interface TableState<TFilter, TItem extends NonNullable<unknown>> {
  filter: TFilter;
  sorting: DataTableSortData<TItem>;
  page: number;
  limit: number;
  /** Highest-intent source since the last URL write. Monotonic; see `raise`. */
  pendingIntent: ChangeSource;
}

/**
 * Every way table state can change. One event in, one batch of effects out: the
 * multi-step mutation that made `fetchDebounce` load-bearing (a filter change firing a
 * second page mutation, hence a second fetch) cannot happen, because the page reset is
 * part of the same reduction.
 */
export type TableEvent<TFilter, TItem extends NonNullable<unknown>> =
  | { type: 'filter-set'; filter: TFilter; source: ChangeSource }
  | { type: 'sort-set'; sorting: DataTableSortData<TItem> }
  | { type: 'page-set'; page: number; source: ChangeSource }
  | { type: 'limit-set'; limit: number }
  | { type: 'param-changed'; to: ParamDestination }
  | {
    type: 'route-applied';
    filter: TFilter;
    sorting: DataTableSortData<TItem>;
    page: number;
    limit: number;
    source: ChangeSource;
  }
  | { type: 'url-committed' };

/**
 * A side effect the adapter runs. Declarative on purpose: the reducer decides what
 * should happen, the adapter owns how (router.push, localStorage, api fetch).
 */
export type Effect =
  | { type: 'persist' }
  | { type: 'push-url' }
  | { type: 'fetch' };

export interface ReduceResult<TFilter, TItem extends NonNullable<unknown>> {
  state: TableState<TFilter, TItem>;
  effects: Effect[];
}

/**
 * Monotonic join on provenance: a real source raises the pending intent, but
 * `programmatic` never lowers it. This is what stops an internal page-1 reset (a
 * `programmatic` change) from swallowing the URL write a user's filter edit earned.
 */
function raise(current: ChangeSource, source: ChangeSource): ChangeSource {
  return source === 'programmatic' ? current : source;
}

/** Builds the effect list in its fixed order: persist, push-url, fetch. */
function effectsOf(flags: { persist?: boolean; pushUrl?: boolean; fetch?: boolean }): Effect[] {
  const list: Effect[] = [];
  if (flags.persist)
    list.push({ type: 'persist' });
  if (flags.pushUrl)
    list.push({ type: 'push-url' });
  if (flags.fetch)
    list.push({ type: 'fetch' });
  return list;
}

/**
 * Applies a filter change, returning to page 1 when the filter actually moved.
 *
 * @remarks
 * The page reset is a state transition, not an intent: it does not attribute a change to the user
 * and so cannot earn a URL write on its own.
 */
function reduceFilterSet<TFilter, TItem extends NonNullable<unknown>>(
  state: TableState<TFilter, TItem>,
  event: Extract<TableEvent<TFilter, TItem>, { type: 'filter-set' }>,
): ReduceResult<TFilter, TItem> {
  const filterChanged = !isEqual(state.filter, event.filter);
  const pendingIntent = raise(state.pendingIntent, event.source);
  // A filter change resets the page; this is a state transition, not an intent.
  const page = filterChanged ? 1 : state.page;
  const changed = filterChanged || page !== state.page;
  return {
    effects: changed ? effectsOf({ fetch: true, persist: true, pushUrl: pendingIntent === 'user' }) : [],
    state: { ...state, filter: event.filter, page, pendingIntent },
  };
}

function reduceSortSet<TFilter, TItem extends NonNullable<unknown>>(
  state: TableState<TFilter, TItem>,
  event: Extract<TableEvent<TFilter, TItem>, { type: 'sort-set' }>,
): ReduceResult<TFilter, TItem> {
  const changed = !isEqual(state.sorting, event.sorting);
  // The table-facing sort model is only written by direct interaction, so 'user'.
  return {
    effects: changed ? effectsOf({ fetch: true, persist: true, pushUrl: true }) : [],
    state: { ...state, pendingIntent: 'user', sorting: event.sorting },
  };
}

function reducePageSet<TFilter, TItem extends NonNullable<unknown>>(
  state: TableState<TFilter, TItem>,
  event: Extract<TableEvent<TFilter, TItem>, { type: 'page-set' }>,
): ReduceResult<TFilter, TItem> {
  const changed = event.page !== state.page;
  const pendingIntent = raise(state.pendingIntent, event.source);
  return {
    effects: changed ? effectsOf({ fetch: true, persist: true, pushUrl: pendingIntent === 'user' }) : [],
    state: { ...state, page: event.page, pendingIntent },
  };
}

/**
 * Applies a page-size change, keeping the current page.
 *
 * @remarks
 * Loading more rows does not reset the page: the offset moving is what makes it fetch. Always a
 * `user` change, since only an interaction sets the page size.
 */
function reduceLimitSet<TFilter, TItem extends NonNullable<unknown>>(
  state: TableState<TFilter, TItem>,
  event: Extract<TableEvent<TFilter, TItem>, { type: 'limit-set' }>,
): ReduceResult<TFilter, TItem> {
  const changed = event.limit !== state.limit;
  return {
    effects: changed ? effectsOf({ fetch: true, persist: true, pushUrl: true }) : [],
    state: { ...state, limit: event.limit, pendingIntent: 'user' },
  };
}

/**
 * Folds a bound param's new value in, according to which sinks that param feeds.
 *
 * @remarks
 * Reaching the request payload (`both`, `request`) resets the page, because the rows under the
 * old offset are no longer the same rows. Reaching the URL (`both`, `url`) attributes the change
 * to the user, which is what earns it a pushed history entry. `request` therefore resets without
 * earning a write, so a param the URL never carried cannot clobber route-driven filter state.
 */
function reduceParamChanged<TFilter, TItem extends NonNullable<unknown>>(
  state: TableState<TFilter, TItem>,
  event: Extract<TableEvent<TFilter, TItem>, { type: 'param-changed' }>,
): ReduceResult<TFilter, TItem> {
  switch (event.to) {
    case 'both':
      return {
        effects: effectsOf({ fetch: true, persist: true, pushUrl: true }),
        state: { ...state, page: 1, pendingIntent: 'user' },
      };
    case 'request':
      return {
        effects: effectsOf({ fetch: true, persist: true }),
        state: { ...state, page: 1 },
      };
    case 'url':
      return {
        effects: effectsOf({ pushUrl: true }),
        state: { ...state, pendingIntent: 'user' },
      };
  }
  return { effects: [], state };
}

/**
 * Adopts the state a navigation carries, wholesale.
 *
 * @remarks
 * A navigation is authoritative: it *sets* the intent to `route` or `restore` rather than raising
 * it, which is the one path that can lower a stale `user` intent left behind by an earlier change.
 */
function reduceRouteApplied<TFilter, TItem extends NonNullable<unknown>>(
  state: TableState<TFilter, TItem>,
  event: Extract<TableEvent<TFilter, TItem>, { type: 'route-applied' }>,
): ReduceResult<TFilter, TItem> {
  // The echo of our own write: skip re-applying state we already hold.
  if (event.source === 'self')
    return { effects: [], state };

  const changed = !isEqual(state.filter, event.filter)
    || !isEqual(state.sorting, event.sorting)
    || state.page !== event.page
    || state.limit !== event.limit;
  return {
    effects: changed ? effectsOf({ fetch: true, persist: true }) : [],
    state: {
      filter: event.filter,
      limit: event.limit,
      page: event.page,
      pendingIntent: event.source,
      sorting: event.sorting,
    },
  };
}

/**
 * Folds one table event into the next state, plus the effects that state change earns.
 *
 * @remarks
 * Pure and synchronous: the effects are returned as data for the caller to run, so nothing here
 * fetches, persists, or touches the router. Every branch is total over the event union, which is
 * what lets the function return without a default case.
 */
export function reduce<TFilter, TItem extends NonNullable<unknown>>(
  state: TableState<TFilter, TItem>,
  event: TableEvent<TFilter, TItem>,
): ReduceResult<TFilter, TItem> {
  switch (event.type) {
    case 'filter-set':
      return reduceFilterSet(state, event);
    case 'sort-set':
      return reduceSortSet(state, event);
    case 'page-set':
      return reducePageSet(state, event);
    case 'limit-set':
      return reduceLimitSet(state, event);
    case 'param-changed':
      return reduceParamChanged(state, event);
    case 'route-applied':
      return reduceRouteApplied(state, event);
    case 'url-committed':
      return { effects: [], state: { ...state, pendingIntent: 'programmatic' } };
  }
}
