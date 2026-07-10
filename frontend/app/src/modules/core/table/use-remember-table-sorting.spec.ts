import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import { mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, type Ref } from 'vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';

interface Row { id: string }

const mockPersist = ref<boolean>(true);

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => mockPersist),
}));

const STORAGE_KEY = 'rotki.table_sorting';

function headers(): Ref<DataTableColumn<Row>[]> {
  return ref<DataTableColumn<Row>[]>([
    { key: 'id', label: 'ID', sortable: true },
    { key: 'name', label: 'Name', sortable: false },
  ]);
}

function mountSorting(sort: Ref<DataTableSortData<Row>>): ReturnType<typeof mount> {
  const component = defineComponent({
    setup() {
      useRememberTableSorting<Row>(TableId.HISTORY, sort, headers());
      return {};
    },
    template: '<div />',
  });
  return mount(component);
}

describe('useRememberTableSorting', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    set(mockPersist, true);
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('should restore a saved sort for the table on mount', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ [TableId.HISTORY]: { column: 'id', direction: 'desc' } }));
    const sort = ref<DataTableSortData<Row>>({ column: 'id', direction: 'asc' });
    mountSorting(sort);
    expect(get(sort)).toStrictEqual({ column: 'id', direction: 'desc' });
  });

  it('should drop saved sorts referencing non-sortable columns', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ [TableId.HISTORY]: { column: 'name', direction: 'desc' } }));
    const sort = ref<DataTableSortData<Row>>({ column: 'id', direction: 'asc' });
    mountSorting(sort);
    expect(get(sort)).toStrictEqual({ column: 'id', direction: 'asc' });
  });

  it('should restore only the sortable entries from a saved array sort', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      [TableId.HISTORY]: [
        { column: 'name', direction: 'asc' },
        { column: 'id', direction: 'desc' },
      ],
    }));
    const sort = ref<DataTableSortData<Row>>([]);
    mountSorting(sort);
    expect(get(sort)).toStrictEqual([{ column: 'id', direction: 'desc' }]);
  });

  it('should not restore anything when persistence is disabled', () => {
    set(mockPersist, false);
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ [TableId.HISTORY]: { column: 'id', direction: 'desc' } }));
    const sort = ref<DataTableSortData<Row>>({ column: 'id', direction: 'asc' });
    mountSorting(sort);
    expect(get(sort)).toStrictEqual({ column: 'id', direction: 'asc' });
  });

  it('should persist sort changes when persistence is enabled', async () => {
    const sort = ref<DataTableSortData<Row>>({ column: 'id', direction: 'asc' });
    mountSorting(sort);

    set(sort, { column: 'id', direction: 'desc' });
    await nextTick();

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
    expect(stored[TableId.HISTORY]).toStrictEqual({ column: 'id', direction: 'desc' });
  });

  it('should remove the stored sort when persistence is disabled and the sort changes', async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ [TableId.HISTORY]: { column: 'id', direction: 'desc' } }));
    set(mockPersist, false);
    const sort = ref<DataTableSortData<Row>>({ column: 'id', direction: 'asc' });
    mountSorting(sort);

    set(sort, { column: 'id', direction: 'asc' });
    await nextTick();

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
    expect(stored[TableId.HISTORY]).toBeUndefined();
  });
});
