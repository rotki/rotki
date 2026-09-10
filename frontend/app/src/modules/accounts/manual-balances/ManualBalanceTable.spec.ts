import type { ManualBalanceWithPrice } from '@/modules/balances/types/manual-balances';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import ManualBalanceTable from '@/modules/accounts/manual-balances/ManualBalanceTable.vue';
import { BalanceType } from '@/modules/balances/types/balances';

const {
  dataSource,
  fetch,
  prepareForEdit,
  pricesLoading,
  refetch,
  refresh,
  refreshing,
  rows,
  showDeleteConfirmation,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    dataSource: ref<unknown[]>([]),
    fetch: vi.fn(async () => ({ data: [], found: 0, limit: 0, total: 0 })),
    prepareForEdit: vi.fn((balance: unknown) => balance),
    pricesLoading: ref<boolean>(false),
    refetch: vi.fn(async () => {}),
    refresh: vi.fn(),
    refreshing: ref<boolean>(false),
    rows: ref<unknown[]>([]),
    showDeleteConfirmation: vi.fn(),
  };
});

vi.mock('@/modules/balances/manual/use-manual-balances-or-liabilities', async () => {
  const { computed } = await import('vue');
  return {
    useManualBalancesOrLiabilities: (): Record<string, unknown> => ({
      dataSource,
      fetch,
      locations: computed(() => []),
    }),
  };
});

vi.mock('@/modules/accounts/manual-balances/use-manual-balance-table-actions', () => ({
  useManualBalanceTableActions: (): Record<string, unknown> => ({
    prepareForEdit,
    pricesLoading,
    refresh,
    refreshing,
    showDeleteConfirmation,
  }),
}));

vi.mock('@/modules/accounts/manual-balances/use-manual-balance-fields', () => ({
  useManualBalanceFields: (): unknown[] => [],
}));

vi.mock('@/modules/core/table/pill/composables/use-pill-bar-labels', () => ({
  usePillBarLabels: (): Record<string, unknown> => ({}),
}));

vi.mock('@/modules/core/table/use-remember-table-sorting', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/table/use-remember-table-sorting')>(),
  useRememberTableSorting: (): void => {},
}));

vi.mock('@/modules/core/table/use-server-table', async () => {
  const { computed, ref } = await import('vue');
  const { useTableEmptyState } = await import('@/modules/core/table/use-table-empty-state');
  return {
    useServerTable: (): Record<string, unknown> => ({
      collection: computed(() => ({ data: rows.value, found: rows.value.length, limit: 10, total: rows.value.length })),
      error: ref(undefined),
      filter: ref({}),
      isLoading: ref(false),
      pagination: ref({ limit: 10, page: 1, total: 0 }),
      refetch,
      sort: ref([]),
    }),
    useTableEmptyState,
  };
});

/** Renders the row actions, which is where the edit and delete of a row are wired. */
const TableStub = defineComponent({
  props: ['cols', 'rows', 'loading', 'sort', 'pagination'],
  template: `<div>
    <template v-for="row in rows" :key="row.identifier">
      <slot name="item.actions" :row="row" />
    </template>
  </div>`,
});

const RowActionsStub = defineComponent({
  emits: ['edit-click', 'delete-click'],
  template: '<div />',
});

function balance(): ManualBalanceWithPrice {
  return {
    amount: bigNumberify(1),
    asset: 'ETH',
    assetIsMissing: false,
    balanceType: BalanceType.ASSET,
    identifier: 1,
    label: 'savings',
    location: 'external',
    price: bigNumberify(2),
    tags: null,
    value: bigNumberify(2),
  };
}

function createWrapper(type: 'balances' | 'liabilities' = 'balances'): VueWrapper<any> {
  return mount(ManualBalanceTable, {
    global: {
      stubs: {
        PillFilterBar: true,
        RefreshButton: { emits: ['refresh'], props: ['loading', 'tooltip'], template: '<button @click="$emit(\'refresh\')" />' },
        RowActions: RowActionsStub,
        RuiCard: { template: '<div><slot name="custom-header" /><slot /></div>' },
        RuiDataTable: TableStub,
      },
    },
    props: { type },
  });
}

function actions(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent(RowActionsStub);
}

describe('manualBalanceTable', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(dataSource, []);
    set(pricesLoading, false);
    set(refreshing, false);
    set(rows, [balance()]);
    prepareForEdit.mockImplementation((value: unknown) => value);
  });

  describe('a row', () => {
    /** The edit dialog takes a plain balance, not the priced row the table holds. */
    it('should hand the parent the balance behind the row', async () => {
      const wrapper = createWrapper();
      prepareForEdit.mockReturnValue({ identifier: 1, label: 'savings' });

      actions(wrapper).vm.$emit('edit-click');
      await nextTick();

      expect(prepareForEdit).toHaveBeenCalledWith(balance());
      expect(wrapper.emitted('edit')?.at(-1)?.[0]).toEqual({ identifier: 1, label: 'savings' });
    });

    it('should confirm before deleting', async () => {
      const wrapper = createWrapper();

      actions(wrapper).vm.$emit('delete-click');
      await nextTick();

      expect(showDeleteConfirmation).toHaveBeenCalledWith(1);
    });
  });

  it('should refresh on request', async () => {
    const wrapper = createWrapper();

    await wrapper.find('button').trigger('click');

    expect(refresh).toHaveBeenCalledTimes(1);
  });

  /** The table is a view onto the balances, so it re-reads whenever they actually change. */
  describe('following the balances', () => {
    it('should fetch on arrival', () => {
      createWrapper();

      expect(refetch).toHaveBeenCalledTimes(1);
    });

    it('should refetch once they change', async () => {
      createWrapper();
      refetch.mockClear();

      set(dataSource, [balance()]);
      await nextTick();

      expect(refetch).toHaveBeenCalledTimes(1);
    });

    /** A store write that lands on the same balances is not a change worth a round trip. */
    it('should not refetch when they are replaced by an equal set', async () => {
      set(dataSource, [balance()]);
      createWrapper();
      refetch.mockClear();

      set(dataSource, [balance()]);
      await nextTick();

      expect(refetch).not.toHaveBeenCalled();
    });
  });

  /** Prices arrive after the rows, so the table re-reads once the fetching settles. */
  describe('following the prices', () => {
    it('should refetch once the prices have finished loading', async () => {
      vi.useFakeTimers();
      createWrapper();
      set(pricesLoading, true);
      await nextTick();
      refetch.mockClear();

      set(pricesLoading, false);
      await vi.advanceTimersByTimeAsync(1100);

      expect(refetch).toHaveBeenCalledTimes(1);
      vi.useRealTimers();
    });

    it('should not refetch when they start loading', async () => {
      vi.useFakeTimers();
      createWrapper();
      refetch.mockClear();

      set(pricesLoading, true);
      await vi.advanceTimersByTimeAsync(1100);

      expect(refetch).not.toHaveBeenCalled();
      vi.useRealTimers();
    });
  });
});
