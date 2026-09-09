import type { AddressBookEntry } from '@/modules/accounts/address-book/eth-names';
import { mount, type VueWrapper } from '@vue/test-utils';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import AddressBookManagement from '@/modules/accounts/address-book/AddressBookManagement.vue';

const { fetch, getAddressBook, refetch } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    fetch: ref<((filter: unknown) => unknown) | undefined>(undefined),
    getAddressBook: vi.fn(async () => ({ data: [], found: 0, limit: 0, total: 0 })),
    refetch: vi.fn(async () => {}),
  };
});

vi.mock('@/modules/accounts/address-book/use-address-book-operations', () => ({
  useAddressBookOperations: (): Record<string, unknown> => ({ getAddressBook }),
}));

vi.mock('@/modules/accounts/address-book/use-address-book-fields', () => ({
  useAddressBookFields: (): unknown[] => [],
}));

vi.mock('@/modules/core/table/pill/composables/use-pill-bar-labels', () => ({
  usePillBarLabels: (): Record<string, unknown> => ({}),
}));

/**
 * Captures the fetch the table was configured with, which is where the location reaches the query,
 * and stands in for the table's own state.
 */
vi.mock('@/modules/core/table/use-server-table', async () => {
  const { computed, ref } = await import('vue');
  return {
    useServerTable: (options: { fetch: (filter: unknown) => unknown }): Record<string, unknown> => {
      fetch.value = options.fetch;
      return {
        collection: computed(() => ({ data: [], found: 0, limit: 0, total: 0 })),
        filter: ref({}),
        isLoading: ref(false),
        pagination: ref({ limit: 10, page: 1, total: 0 }),
        refetch,
        sort: ref([]),
      };
    },
  };
});

const TableStub = defineComponent({
  emits: ['edit', 'refresh'],
  props: ['collection', 'location', 'loading', 'blockchain', 'sort', 'pagination'],
  template: '<div />',
});

const DialogStub = defineComponent({
  emits: ['update:open', 'update-tab', 'refresh'],
  props: ['open', 'editableItem', 'editMode', 'selectedChain', 'location'],
  template: '<div />',
});

const TabsStub = defineComponent({
  emits: ['update:modelValue'],
  props: ['modelValue'],
  template: '<div><slot /></div>',
});

function createWrapper(): VueWrapper<any> {
  return mount(AddressBookManagement, {
    global: {
      stubs: {
        AddressBookFormDialog: DialogStub,
        AddressBookManagementMore: true,
        AddressBookTable: TableStub,
        EthNamesHint: true,
        PillFilterBar: true,
        RuiTab: true,
        RuiTabItem: { template: '<div><slot /></div>' },
        RuiTabItems: { template: '<div><slot /></div>' },
        RuiTabs: TabsStub,
        TablePageLayout: { template: '<div><slot name="buttons" /><slot /></div>' },
      },
    },
  });
}

function dialog(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent(DialogStub);
}

function entry(): AddressBookEntry {
  return { address: '0x9531C059098e3d194fF87FebB587aB07B30B1306', blockchain: 'eth', name: 'mine' };
}

async function switchToPrivate(wrapper: VueWrapper<any>): Promise<void> {
  wrapper.findComponent(TabsStub).vm.$emit('update:modelValue', 1);
  await nextTick();
}

describe('addressBookManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
  });

  /** The tab strip is the scope of everything below it, so the tab index picks the address book. */
  describe('the scope tabs', () => {
    it('should start on the global address book', () => {
      expect(dialog(createWrapper()).props('location')).toBe('global');
    });

    it('should switch to the private one', async () => {
      const wrapper = createWrapper();

      await switchToPrivate(wrapper);

      expect(dialog(wrapper).props('location')).toBe('private');
    });

    it('should query the address book of the tab in view', async () => {
      const wrapper = createWrapper();
      await switchToPrivate(wrapper);

      const query = get(fetch);
      assert(query);
      await query({});

      expect(getAddressBook).toHaveBeenCalledWith('private', {});
    });

    /** Each book holds its own entries, so switching tabs has to go back to the backend. */
    it('should refetch when the tab changes', async () => {
      const wrapper = createWrapper();
      refetch.mockClear();

      await switchToPrivate(wrapper);

      expect(refetch).toHaveBeenCalledTimes(1);
    });

    it('should fetch once on arrival, before any tab is touched', () => {
      createWrapper();

      expect(refetch).toHaveBeenCalledTimes(1);
    });
  });

  /** The dialog both adds and edits, and what it does is decided by what it was seeded with. */
  describe('the form dialog', () => {
    it('should stay closed until it is asked for', () => {
      expect(dialog(createWrapper()).props('open')).toBe(false);
    });

    it('should open empty for an addition', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=address-book-add]').trigger('click');

      expect(dialog(wrapper).props('open')).toBe(true);
      expect(dialog(wrapper).props('editableItem')).toBeNull();
      expect(dialog(wrapper).props('editMode')).toBe(false);
    });

    /** The dialog is reused, so an addition after an edit must not reopen on the edited entry. */
    it('should open empty for an addition following an edit', async () => {
      const wrapper = createWrapper();
      wrapper.findComponent(TableStub).vm.$emit('edit', entry());
      await nextTick();

      await wrapper.find('[data-testid=address-book-add]').trigger('click');

      expect(dialog(wrapper).props('editableItem')).toBeNull();
      expect(dialog(wrapper).props('editMode')).toBe(false);
    });

    it('should open on the entry being edited', async () => {
      const wrapper = createWrapper();

      wrapper.findComponent(TableStub).vm.$emit('edit', entry());
      await nextTick();

      expect(dialog(wrapper).props('open')).toBe(true);
      expect(dialog(wrapper).props('editMode')).toBe(true);
    });

    /** An entry carries no book of its own, so the one in view is what it is saved back into. */
    it('should edit the entry into the book in view', async () => {
      const wrapper = createWrapper();
      await switchToPrivate(wrapper);

      wrapper.findComponent(TableStub).vm.$emit('edit', entry());
      await nextTick();

      expect(dialog(wrapper).props('editableItem')).toEqual({ ...entry(), location: 'private' });
    });

    it('should follow the dialog moving to another tab', async () => {
      const wrapper = createWrapper();

      dialog(wrapper).vm.$emit('update-tab', 1);
      await nextTick();

      expect(dialog(wrapper).props('location')).toBe('private');
    });

    it('should reload the table once an entry is saved', async () => {
      const wrapper = createWrapper();
      refetch.mockClear();

      dialog(wrapper).vm.$emit('refresh');
      await nextTick();

      expect(refetch).toHaveBeenCalledTimes(1);
    });
  });
});
