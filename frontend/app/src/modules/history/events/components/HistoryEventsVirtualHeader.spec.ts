import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { Ref } from 'vue';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import HistoryEventsVirtualHeader from '@/modules/history/events/components/HistoryEventsVirtualHeader.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { globalItemsPerPage } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { globalItemsPerPage: ref<number>(10) };
});

vi.mock('@/modules/session/use-items-per-page', () => ({
  useItemsPerPage: (): Ref<number> => globalItemsPerPage,
}));

const MenuSelectStub = {
  name: 'RuiMenuSelect',
  props: ['modelValue', 'options', 'dense', 'hideDetails', 'classNames'],
  template: '<div />',
};

function createWrapper(
  pagination: TablePaginationData,
  sort: DataTableSortData<HistoryEventEntry> = [],
): VueWrapper<any> {
  return mount(HistoryEventsVirtualHeader, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: { RuiMenuSelect: MenuSelectStub },
    },
    props: { pagination, sort },
  });
}

function page(pagination: Partial<TablePaginationData> = {}): TablePaginationData {
  return { limit: 10, page: 1, total: 100, ...pagination };
}

function lastPagination(wrapper: VueWrapper<any>): TablePaginationData | undefined {
  return wrapper.emitted<[TablePaginationData]>('update:pagination')?.at(-1)?.[0];
}

describe('historyEventsVirtualHeader', () => {
  beforeEach(() => {
    set(globalItemsPerPage, 10);
  });

  describe('sorting', () => {
    it('should start the sort descending when the control is first pressed', async () => {
      const wrapper = createWrapper(page());

      await wrapper.find('[data-testid=events-sort-date]').trigger('click');

      expect(wrapper.emitted<[unknown]>('update:sort')?.at(-1)?.[0])
        .toEqual([{ column: 'timestamp', direction: 'desc' }]);
    });

    it('should reverse a sort already in force', async () => {
      const wrapper = createWrapper(page(), [{ column: 'timestamp', direction: 'desc' }]);

      await wrapper.find('[data-testid=events-sort-date]').trigger('click');

      expect(wrapper.emitted<[unknown]>('update:sort')?.at(-1)?.[0])
        .toEqual([{ column: 'timestamp', direction: 'asc' }]);
    });
  });

  describe('paging', () => {
    it('should move to the next page', async () => {
      const wrapper = createWrapper(page({ page: 2 }));

      await wrapper.find('[data-testid=events-page-next]').trigger('click');

      expect(lastPagination(wrapper)).toMatchObject({ page: 3 });
    });

    it('should jump back to the first page', async () => {
      const wrapper = createWrapper(page({ page: 5 }));

      await wrapper.find('[data-testid=events-page-first]').trigger('click');

      expect(lastPagination(wrapper)).toMatchObject({ page: 1 });
    });

    it('should not offer the first page while already on it', () => {
      const wrapper = createWrapper(page({ page: 1 }));

      expect(wrapper.find('[data-testid=events-page-first]').attributes('disabled')).toBeDefined();
    });

    it('should not offer a next page from the last one', () => {
      const wrapper = createWrapper(page({ limit: 10, page: 10, total: 100 }));

      expect(wrapper.find('[data-testid=events-page-next]').attributes('disabled')).toBeDefined();
    });

    it('should offer a next page while rows remain', () => {
      const wrapper = createWrapper(page({ limit: 10, page: 9, total: 100 }));

      expect(wrapper.find('[data-testid=events-page-next]').attributes('disabled')).toBeUndefined();
    });
  });

  describe('the page size', () => {
    it('should return to the first page when it changes', async () => {
      const wrapper = createWrapper(page({ page: 7 }));

      await wrapper.findComponent(MenuSelectStub).vm.$emit('update:modelValue', 50);

      expect(lastPagination(wrapper)).toMatchObject({ limit: 50, page: 1 });
    });

    /** The size is a preference, so choosing it here is choosing it for every table. */
    it('should become the account-wide preference', async () => {
      const wrapper = createWrapper(page());

      await wrapper.findComponent(MenuSelectStub).vm.$emit('update:modelValue', 50);

      expect(get(globalItemsPerPage)).toBe(50);
    });

    it('should show the size the table is currently paging by', () => {
      const wrapper = createWrapper(page({ limit: 25 }));

      expect(wrapper.findComponent(MenuSelectStub).props('modelValue')).toBe(25);
    });
  });

  describe('the range on show', () => {
    it('should count from one on the first page', () => {
      const wrapper = createWrapper(page({ limit: 10, page: 1, total: 100 }));

      expect(wrapper.find('[data-testid=events-page-range]').text()).toContain('1-10');
    });

    it('should stop at the last row rather than the page size', () => {
      const wrapper = createWrapper(page({ limit: 10, page: 3, total: 25 }));

      expect(wrapper.find('[data-testid=events-page-range]').text()).toContain('21-25');
    });
  });
});
