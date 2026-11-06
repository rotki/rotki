import type { ManualBalanceWithPrice } from '@/modules/balances/types/manual-balances';
import type { NamedFailure } from '@/modules/shell/components/named-failure';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import ManualBalanceTable from '@/modules/accounts/manual-balances/ManualBalanceTable.vue';
import { BalanceType } from '@/modules/balances/types/balances';

const {
  dataSource,
  deleteFailure,
  deleteRow,
  fetch,
  prepareForEdit,
  pricesLoading,
  refetch,
  rows,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    dataSource: ref<unknown[]>([]),
    deleteFailure: ref<NamedFailure>(),
    deleteRow: vi.fn<(id: number) => Promise<void>>(async () => {}),
    fetch: vi.fn(async () => ({ data: [], found: 0, limit: 0, total: 0 })),
    prepareForEdit: vi.fn((balance: unknown) => balance),
    pricesLoading: ref<boolean>(false),
    refetch: vi.fn(async () => {}),
    rows: ref<unknown[]>([]),
  };
});

const deleteConfirm = { message: 'delete it?', title: 'Delete balance' };

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
    deleteConfirm,
    deleteFailure,
    deleteRow,
    prepareForEdit,
    pricesLoading,
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
  props: ['deleteConfirm'],
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
        RowActions: RowActionsStub,
        RuiDataTable: TableStub,
        TableFrame: { template: '<div><div data-testid="toolbar"><slot name="toolbar" /></div><slot /></div>' },
      },
    },
    props: { type },
    slots: { toolbar: '<span data-testid="toolbar-control" />' },
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
    set(deleteFailure, undefined);
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

    it('should have its delete button ask before deleting', () => {
      const wrapper = createWrapper();

      expect(actions(wrapper).props('deleteConfirm')).toEqual(deleteConfirm);
    });

    it('should delete the balance behind the row once the delete is confirmed', async () => {
      const wrapper = createWrapper();

      actions(wrapper).vm.$emit('delete-click');
      await nextTick();

      expect(deleteRow).toHaveBeenCalledWith(1);
    });
  });

  describe('a failed delete', () => {
    it('should be named above the rows, without a retry', async () => {
      const wrapper = createWrapper();

      set(deleteFailure, { failure: 'backend said no', title: 'Could not delete' });
      await nextTick();

      const strip = wrapper.find('[data-testid=manual-balances-delete-error]');
      expect(strip.text()).toContain('Could not delete');
      expect(strip.text()).toContain('backend said no');
      expect(strip.find('[data-testid=failure-strip-retry]').exists()).toBe(false);
    });

    it('should show nothing while no delete has failed', () => {
      const wrapper = createWrapper();

      expect(wrapper.find('[data-testid=manual-balances-delete-error]').exists()).toBe(false);
    });
  });

  /** The page puts its assets / liabilities switch in the table's toolbar, ahead of the filter. */
  it('should render the controls it is given in its toolbar', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=toolbar] [data-testid=toolbar-control]').exists()).toBe(true);
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
