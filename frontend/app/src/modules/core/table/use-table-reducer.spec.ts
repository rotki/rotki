import type { DataTableSortData } from '@rotki/ui-library';
import { describe, expect, it } from 'vitest';
import { type Effect, reduce, type TableState } from '@/modules/core/table/use-table-reducer';

interface Filter {
  q?: string;
}

interface Item {
  id: number;
}

type State = TableState<Filter, Item>;

const SORT_ASC: DataTableSortData<Item> = { column: 'id', direction: 'asc' };
const SORT_DESC: DataTableSortData<Item> = { column: 'id', direction: 'desc' };

function makeState(overrides: Partial<State> = {}): State {
  return {
    filter: {},
    limit: 10,
    page: 1,
    pendingIntent: 'programmatic',
    sorting: SORT_ASC,
    ...overrides,
  };
}

/** The effect types in order, so a test reads the fixed persist/push-url/fetch order. */
function effectTypes(effects: Effect[]): string[] {
  return effects.map(effect => effect.type);
}

describe('table reducer', () => {
  describe('filter-set', () => {
    it('should reset the page and emit persist/push-url/fetch on a user filter change', () => {
      const { state, effects } = reduce(makeState({ page: 3 }), {
        filter: { q: 'a' },
        source: 'user',
        type: 'filter-set',
      });

      expect(state.page).toBe(1);
      expect(state.filter).toEqual({ q: 'a' });
      expect(state.pendingIntent).toBe('user');
      expect(effectTypes(effects)).toEqual(['persist', 'push-url', 'fetch']);
    });

    it('should emit no effects when the filter is unchanged', () => {
      const { state, effects } = reduce(makeState({ filter: { q: 'a' } }), {
        filter: { q: 'a' },
        source: 'user',
        type: 'filter-set',
      });

      expect(effects).toEqual([]);
      // Intent is still raised even with no change, matching today's markUserIntent.
      expect(state.pendingIntent).toBe('user');
    });

    it('should omit push-url when the filter change carries no user intent', () => {
      const { state, effects } = reduce(makeState({ page: 3 }), {
        filter: { q: 'a' },
        source: 'programmatic',
        type: 'filter-set',
      });

      expect(state.page).toBe(1);
      expect(state.pendingIntent).toBe('programmatic');
      expect(effectTypes(effects)).toEqual(['persist', 'fetch']);
    });
  });

  describe('provenance is monotonic', () => {
    it('should keep a pending user intent through a programmatic page reset', () => {
      // The exact trap: a user filter edit set intent to 'user', then an internal
      // page-1 reset arrives as 'programmatic'. It must not lower the intent, or the
      // URL write the user earned is swallowed.
      const { state, effects } = reduce(makeState({ page: 3, pendingIntent: 'user' }), {
        page: 1,
        source: 'programmatic',
        type: 'page-set',
      });

      expect(state.pendingIntent).toBe('user');
      expect(effectTypes(effects)).toContain('push-url');
    });
  });

  describe('sort-set', () => {
    it('should mark user intent and emit persist/push-url/fetch on a sort change', () => {
      const { state, effects } = reduce(makeState(), { sorting: SORT_DESC, type: 'sort-set' });

      expect(state.sorting).toEqual(SORT_DESC);
      expect(state.page).toBe(1);
      expect(state.pendingIntent).toBe('user');
      expect(effectTypes(effects)).toEqual(['persist', 'push-url', 'fetch']);
    });

    it('should emit no effects when the sorting is unchanged', () => {
      const { effects } = reduce(makeState({ sorting: SORT_ASC }), { sorting: SORT_ASC, type: 'sort-set' });
      expect(effects).toEqual([]);
    });
  });

  describe('page-set', () => {
    it('should emit effects and mark user intent on a user page change', () => {
      const { state, effects } = reduce(makeState(), { page: 4, source: 'user', type: 'page-set' });

      expect(state.page).toBe(4);
      expect(state.pendingIntent).toBe('user');
      expect(effectTypes(effects)).toEqual(['persist', 'push-url', 'fetch']);
    });

    it('should emit no effects when the page is unchanged', () => {
      const { effects } = reduce(makeState({ page: 2 }), { page: 2, source: 'user', type: 'page-set' });
      expect(effects).toEqual([]);
    });

    it('should omit push-url on a programmatic page change', () => {
      const { state, effects } = reduce(makeState(), { page: 2, source: 'programmatic', type: 'page-set' });

      expect(state.pendingIntent).toBe('programmatic');
      expect(effectTypes(effects)).toEqual(['persist', 'fetch']);
    });
  });

  describe('limit-set', () => {
    it('should fetch without resetting the page on a limit change', () => {
      const { state, effects } = reduce(makeState({ limit: 10, page: 3 }), { limit: 50, type: 'limit-set' });

      expect(state.limit).toBe(50);
      expect(state.page).toBe(3);
      expect(state.pendingIntent).toBe('user');
      expect(effectTypes(effects)).toEqual(['persist', 'push-url', 'fetch']);
    });

    it('should emit no effects when the limit is unchanged', () => {
      const { effects } = reduce(makeState({ limit: 25 }), { limit: 25, type: 'limit-set' });
      expect(effects).toEqual([]);
    });
  });

  describe('param-changed', () => {
    it('should reset the page, mark user intent, and emit all effects for a both-param', () => {
      const { state, effects } = reduce(makeState({ page: 3 }), { to: 'both', type: 'param-changed' });

      expect(state.page).toBe(1);
      expect(state.pendingIntent).toBe('user');
      expect(effectTypes(effects)).toEqual(['persist', 'push-url', 'fetch']);
    });

    it('should reset the page WITHOUT user intent for a request-param (the 8b fix)', () => {
      const { state, effects } = reduce(makeState({ page: 3, pendingIntent: 'programmatic' }), {
        to: 'request',
        type: 'param-changed',
      });

      expect(state.page).toBe(1);
      // request-only params never reach the URL, so no intent and no push-url: that is
      // what stops the page reset from clobbering route-driven filter state.
      expect(state.pendingIntent).toBe('programmatic');
      expect(effectTypes(effects)).toEqual(['persist', 'fetch']);
    });

    it('should not lower a pending user intent on a request-param change', () => {
      const { state } = reduce(makeState({ pendingIntent: 'user' }), { to: 'request', type: 'param-changed' });
      expect(state.pendingIntent).toBe('user');
    });

    it('should push the URL without resetting the page or fetching for a url-param', () => {
      const { state, effects } = reduce(makeState({ page: 3 }), { to: 'url', type: 'param-changed' });

      expect(state.page).toBe(3);
      expect(state.pendingIntent).toBe('user');
      expect(effectTypes(effects)).toEqual(['push-url']);
    });
  });

  describe('route-applied', () => {
    it('should no-op on the echo of our own write', () => {
      const before = makeState({ filter: { q: 'a' }, page: 2 });
      const { state, effects } = reduce(before, {
        filter: { q: 'z' },
        limit: 10,
        page: 9,
        sorting: SORT_ASC,
        source: 'self',
        type: 'route-applied',
      });

      expect(state).toBe(before);
      expect(effects).toEqual([]);
    });

    it('should adopt route state and emit persist/fetch on a real navigation', () => {
      const { state, effects } = reduce(makeState(), {
        filter: { q: 'z' },
        limit: 25,
        page: 3,
        sorting: SORT_DESC,
        source: 'route',
        type: 'route-applied',
      });

      expect(state).toMatchObject({ filter: { q: 'z' }, limit: 25, page: 3, pendingIntent: 'route', sorting: SORT_DESC });
      expect(effectTypes(effects)).toEqual(['persist', 'fetch']);
    });

    it('should lower a stale user intent on navigation', () => {
      const { state } = reduce(makeState({ pendingIntent: 'user' }), {
        filter: { q: 'z' },
        limit: 10,
        page: 1,
        sorting: SORT_ASC,
        source: 'route',
        type: 'route-applied',
      });

      expect(state.pendingIntent).toBe('route');
    });

    it('should set intent but emit nothing when the route matches current state', () => {
      const current = makeState({ filter: { q: 'a' }, limit: 10, page: 2, sorting: SORT_ASC });
      const { state, effects } = reduce(current, {
        filter: { q: 'a' },
        limit: 10,
        page: 2,
        sorting: SORT_ASC,
        source: 'restore',
        type: 'route-applied',
      });

      expect(state.pendingIntent).toBe('restore');
      expect(effects).toEqual([]);
    });
  });

  describe('url-committed', () => {
    it('should lower the intent to programmatic after a real push', () => {
      const { state, effects } = reduce(makeState({ pendingIntent: 'user' }), { type: 'url-committed' });

      expect(state.pendingIntent).toBe('programmatic');
      expect(effects).toEqual([]);
    });
  });
});
