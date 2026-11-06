import type { AddressBookEntry, AddressBookLocation } from '@/modules/accounts/address-book/eth-names';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, type MaybeRefOrGetter, toValue } from 'vue';
import AddressBookTable from '@/modules/accounts/address-book/AddressBookTable.vue';

const { deleteEntry, locations } = vi.hoisted(() => {
  const locations: AddressBookLocation[] = [];
  return {
    deleteEntry: vi.fn<(item: AddressBookEntry) => Promise<void>>(async () => {}),
    locations,
  };
});

vi.mock('@/modules/accounts/address-book/use-address-book-deletion', () => ({
  useAddressBookDeletion: (location: MaybeRefOrGetter<AddressBookLocation>): Record<string, unknown> => ({
    deleteConfirm: (item: AddressBookEntry): { title: string; message: string } => ({
      message: `delete ${item.address}?`,
      title: 'Delete entry',
    }),
    deleteEntry: async (item: AddressBookEntry): Promise<void> => {
      locations.push(toValue(location));
      await deleteEntry(item);
    },
  }),
}));

vi.mock('@/modules/core/table/use-remember-table-sorting', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/table/use-remember-table-sorting')>(),
  useRememberTableSorting: (): void => {},
}));

/** Renders only the actions cell of each row, which is where a row's delete is wired. */
const TableStub = defineComponent({
  props: ['rows'],
  template: `<div>
    <template v-for="row in rows" :key="row.address">
      <slot name="item.actions" :row="row" />
    </template>
  </div>`,
});

const RowActionsStub = defineComponent({
  emits: ['edit-click', 'delete-click'],
  props: ['deleteConfirm'],
  template: '<div />',
});

const entry: AddressBookEntry = { address: '0xabc', blockchain: 'eth', name: 'mine' };

function createWrapper(location: AddressBookLocation = 'private'): VueWrapper<any> {
  return mount(AddressBookTable, {
    global: {
      stubs: { AccountDisplay: true, RowActions: RowActionsStub, RuiDataTable: TableStub },
    },
    props: {
      collection: { data: [entry], found: 1, limit: 10, total: 1 },
      loading: false,
      location,
      pagination: { limit: 10, page: 1, total: 1 },
      sort: [],
    },
  });
}

describe('addressBookTable', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    locations.length = 0;
  });

  it('should have the row\'s delete button ask about that entry first', () => {
    const wrapper = createWrapper();

    expect(wrapper.findComponent(RowActionsStub).props('deleteConfirm')).toEqual({
      message: 'delete 0xabc?',
      title: 'Delete entry',
    });
  });

  it('should delete the row\'s entry from the book in view once confirmed', async () => {
    const wrapper = createWrapper('global');

    wrapper.findComponent(RowActionsStub).vm.$emit('delete-click');
    await nextTick();

    expect(deleteEntry).toHaveBeenCalledWith(entry);
    expect(locations).toEqual(['global']);
  });
});
