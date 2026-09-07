import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type Ref, ref } from 'vue';
import { useMappingAdmin } from './use-mapping-admin';

interface RouteHolder {
  route?: Ref<{ query: Record<string, string> }>;
}

/**
 * The global `vue-router` mock exposes `push` but no `replace`, and hands back a plain object rather
 * than a ref, so `get(route)` reads undefined. This spec needs both, so it mocks locally.
 */
const { held, replace } = vi.hoisted(() => {
  const held: RouteHolder = {};
  return { held, replace: vi.fn(async () => Promise.resolve()) };
});

vi.mock('vue-router', async () => {
  const { ref: actualRef } = await vi.importActual<typeof import('vue')>('vue');
  held.route = actualRef({ query: {} });
  return {
    useRoute: (): unknown => held.route,
    useRouter: (): Record<string, unknown> => ({ replace }),
  };
});

function setQuery(query: Record<string, string>): void {
  assert(held.route);
  set(held.route, { query });
}

interface CexMapping {
  asset: string;
  location: string;
  locationSymbol: string;
}

interface CexFilters extends Record<string, string | string[] | undefined> {
  location?: string | string[];
  locationSymbol?: string | string[];
}

let filter: Ref<CexFilters>;
let scope: ReturnType<typeof effectScope>;

function admin(): ReturnType<typeof useMappingAdmin<CexMapping, CexFilters>> {
  scope = effectScope();
  return scope.run(() => useMappingAdmin<CexMapping, CexFilters>({
    blank: () => ({ asset: '', location: '', locationSymbol: '' }),
    filter,
    seedFromFilter: { location: 'location', locationSymbol: 'locationSymbol' },
    seedFromQuery: { location: 'location', locationSymbol: 'locationSymbol' },
  }))!;
}

describe('modules/assets/admin/useMappingAdmin', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    filter = ref<CexFilters>({});
    setQuery({});
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('adding a mapping', () => {
    it('should open the dialog closed to editing', () => {
      const { add, editMode, modelValue } = admin();
      add();

      expect(get(editMode)).toBe(false);
      expect(get(modelValue)).toEqual({ asset: '', location: '', locationSymbol: '' });
    });

    it('should seed from whatever the filter is narrowed to', () => {
      set(filter, { location: 'kraken', locationSymbol: 'XBT' });

      const { add, modelValue } = admin();
      add();

      expect(get(modelValue)).toEqual({ asset: '', location: 'kraken', locationSymbol: 'XBT' });
    });

    it('should take the first value when the filter holds a list', () => {
      set(filter, { location: ['kraken', 'binance'] });

      const { add, modelValue } = admin();
      add();

      expect(get(modelValue)?.location).toBe('kraken');
    });

    it('should leave a field the filter does not narrow empty', () => {
      set(filter, { location: 'kraken' });

      const { add, modelValue } = admin();
      add();

      expect(get(modelValue)?.locationSymbol).toBe('');
    });

    it('should leave a field out when its seed maps nowhere', () => {
      set(filter, { location: 'kraken', locationSymbol: 'XBT' });

      scope = effectScope();
      const { add, modelValue } = scope.run(() => useMappingAdmin<CexMapping, CexFilters>({
        blank: () => ({ asset: '', location: '', locationSymbol: '' }),
        filter,
        seedFromFilter: { location: 'location', locationSymbol: undefined },
        seedFromQuery: { location: undefined },
      }))!;
      add();

      expect(get(modelValue)).toEqual({ asset: '', location: 'kraken', locationSymbol: '' });
    });

    it('should let the caller override a seeded field', () => {
      set(filter, { location: 'kraken' });

      const { add, modelValue } = admin();
      add({ location: 'binance' });

      expect(get(modelValue)?.location).toBe('binance');
    });

    it('should start from a fresh blank each time', () => {
      const { add, modelValue } = admin();
      add({ asset: 'BTC' });
      add();

      expect(get(modelValue)?.asset).toBe('');
    });
  });

  describe('editing a mapping', () => {
    it('should open the dialog on the mapping, in edit mode', () => {
      const existing: CexMapping = { asset: 'BTC', location: 'kraken', locationSymbol: 'XBT' };

      const { edit, editMode, modelValue } = admin();
      edit(existing);

      expect(get(editMode)).toBe(true);
      expect(get(modelValue)).toEqual(existing);
    });

    it('should go back to adding after an edit', () => {
      const { add, edit, editMode } = admin();
      edit({ asset: 'BTC', location: 'kraken', locationSymbol: 'XBT' });
      add();

      expect(get(editMode)).toBe(false);
    });
  });

  describe('an ?add= link', () => {
    it('should do nothing when the query does not ask for it', async () => {
      const { consumeAddQuery, modelValue } = admin();

      expect(await consumeAddQuery()).toBe(false);
      expect(get(modelValue)).toBeUndefined();
      expect(replace).not.toHaveBeenCalled();
    });

    it('should open the dialog seeded from the query', async () => {
      setQuery({ add: 'true', location: 'coinbase', locationSymbol: 'ETH' });

      const { consumeAddQuery, modelValue } = admin();

      expect(await consumeAddQuery()).toBe(true);
      expect(get(modelValue)).toEqual({ asset: '', location: 'coinbase', locationSymbol: 'ETH' });
    });

    it('should clear the query so a reload does not reopen it', async () => {
      setQuery({ add: 'true', location: 'coinbase' });

      const { consumeAddQuery } = admin();
      await consumeAddQuery();

      expect(replace).toHaveBeenCalledWith({ query: {} });
    });

    it('should let the query win over the filter', async () => {
      set(filter, { location: 'kraken', locationSymbol: 'XBT' });
      setQuery({ add: 'true', location: 'coinbase', locationSymbol: 'ETH' });

      const { consumeAddQuery, modelValue } = admin();
      await consumeAddQuery();

      expect(get(modelValue)).toEqual({ asset: '', location: 'coinbase', locationSymbol: 'ETH' });
    });

    it('should leave a field out when its query seed maps nowhere', async () => {
      setQuery({ add: 'true', location: 'coinbase', locationSymbol: 'ETH' });

      scope = effectScope();
      const { consumeAddQuery, modelValue } = scope.run(() => useMappingAdmin<CexMapping, CexFilters>({
        blank: () => ({ asset: '', location: '', locationSymbol: '' }),
        filter,
        seedFromFilter: {},
        seedFromQuery: { location: 'location', locationSymbol: undefined },
      }))!;
      await consumeAddQuery();

      expect(get(modelValue)).toEqual({ asset: '', location: 'coinbase', locationSymbol: '' });
    });

    it('should blank a field the query omits rather than fall back to the filter', async () => {
      set(filter, { location: 'kraken', locationSymbol: 'XBT' });
      setQuery({ add: 'true', location: 'coinbase' });

      const { consumeAddQuery, modelValue } = admin();
      await consumeAddQuery();

      expect(get(modelValue)?.locationSymbol).toBe('');
    });
  });
});
