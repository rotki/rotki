import type { Collection } from '@/modules/core/common/collection';
import type { MissingMapping } from '@/modules/user-data/schemas';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type Ref, ref } from 'vue';
import { useAssetMissingMappings } from './use-asset-missing-mappings';

let mappings: Ref<Collection<MissingMapping>>;

const { getData, refetch, remove } = vi.hoisted(() => ({
  getData: vi.fn(),
  refetch: vi.fn(async () => Promise.resolve()),
  remove: vi.fn(async () => Promise.resolve()),
}));

vi.mock('@/modules/assets/admin/missing-mappings/use-missing-mappings-db', () => ({
  useMissingMappingsDB: (): Record<string, unknown> => ({ getData, remove }),
}));

vi.mock('@/modules/assets/admin/missing-mappings/use-missing-mappings-fields', () => ({
  useMissingMappingsFields: (): Record<string, unknown> => ({}),
}));

vi.mock('@/modules/core/table/use-server-table', () => ({
  useServerTable: (): Record<string, unknown> => ({
    collection: mappings,
    filter: ref({}),
    pagination: ref({ limit: 10, page: 1, total: 0 }),
    refetch,
    sort: ref([]),
  }),
}));

function missing(overrides: Partial<MissingMapping> = {}): MissingMapping {
  return { details: '', id: 1, identifier: 'XBT', location: 'kraken', name: 'Kraken', ...overrides };
}

let scope: ReturnType<typeof effectScope>;

function page(): ReturnType<typeof useAssetMissingMappings> {
  scope = effectScope();
  return scope.run(() => useAssetMissingMappings())!;
}

describe('modules/assets/admin/missing-mappings/useAssetMissingMappings', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mappings = ref<Collection<MissingMapping>>({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
      totalValue: undefined,
    });
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('the columns', () => {
    it('should offer location, asset, details and actions', () => {
      const { cols } = page();

      expect(get(cols).map(col => col.key)).toEqual(['location', 'identifier', 'details', 'actions']);
    });

    it('should let the user sort by location and asset only', () => {
      const { cols } = page();

      expect(get(cols).map(col => !!col.sortable)).toEqual([true, true, false, false]);
    });
  });

  describe('starting to add a mapping', () => {
    it('should seed the exchange and its symbol from the row', () => {
      const { modelMapping, onAddClick } = page();
      onAddClick(missing({ identifier: 'XBT', location: 'kraken' }));

      expect(get(modelMapping)).toEqual({ asset: '', location: 'kraken', locationSymbol: 'XBT' });
    });

    it('should leave the asset for the user to choose', () => {
      const { modelMapping, onAddClick } = page();
      onAddClick(missing());

      expect(get(modelMapping)?.asset).toBe('');
    });

    it('should hold nothing before a row is picked', () => {
      const { modelMapping } = page();

      expect(get(modelMapping)).toBeUndefined();
    });
  });

  describe('once a mapping has been added', () => {
    it('should drop the row it was added for and re-read the page', async () => {
      const { onAddComplete } = page();
      await onAddComplete({ asset: 'BTC', location: 'kraken', locationSymbol: 'XBT' });

      expect(remove).toHaveBeenCalledWith({ identifier: 'XBT', location: 'kraken' });
      expect(refetch).toHaveBeenCalledOnce();
    });

    it('should record an all-exchanges mapping against no location', async () => {
      const { onAddComplete } = page();
      await onAddComplete({ asset: 'BTC', location: null, locationSymbol: 'XBT' });

      expect(remove).toHaveBeenCalledWith({ identifier: 'XBT', location: '' });
    });

    it('should re-read the page only after the row is dropped', async () => {
      const order: string[] = [];
      remove.mockImplementation(async () => {
        order.push('remove');
        return Promise.resolve();
      });
      refetch.mockImplementation(async () => {
        order.push('refetch');
        return Promise.resolve();
      });

      const { onAddComplete } = page();
      await onAddComplete({ asset: 'BTC', location: 'kraken', locationSymbol: 'XBT' });

      expect(order).toEqual(['remove', 'refetch']);
    });
  });
});
