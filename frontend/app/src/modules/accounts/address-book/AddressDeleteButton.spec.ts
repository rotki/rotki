import type { AddressBookEntry, AddressBookLocation } from '@/modules/accounts/address-book/eth-names';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type MaybeRefOrGetter, toValue } from 'vue';
import AddressDeleteButton from '@/modules/accounts/address-book/AddressDeleteButton.vue';
import { AddressNamePriority } from '@/modules/accounts/address-book/types/address-name-priorities';

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

function createWrapper(source: string | null = AddressNamePriority.PRIVATE_ADDRESSBOOK): VueWrapper<any> {
  return mount(AddressDeleteButton, {
    global: {
      stubs: { RuiTooltip: { template: '<div><slot name="activator" /></div>' } },
    },
    props: { source, text: '0xabc' },
  });
}

describe('addressDeleteButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    locations.length = 0;
  });

  it('should offer nothing for a name that does not come from an address book', () => {
    const wrapper = createWrapper(AddressNamePriority.ENS_NAMES);

    expect(wrapper.find('[data-testid=address-delete]').exists()).toBe(false);
  });

  it('should ask in place, without deleting, when the trash is clicked', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=address-delete]').trigger('click');

    const question = wrapper.find('[data-testid=inline-confirm]');
    expect(question.attributes('aria-label')).toBe('Delete entry');
    expect(question.text()).toContain('delete 0xabc?');
    expect(wrapper.find('[data-testid=address-delete]').exists()).toBe(false);
    expect(deleteEntry).not.toHaveBeenCalled();
  });

  it('should delete the address for every chain once the question is accepted', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=address-delete]').trigger('click');
    await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');
    await flushPromises();

    expect(deleteEntry).toHaveBeenCalledWith({ address: '0xabc', blockchain: null, name: '' });
    expect(locations).toEqual(['private']);
    expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
  });

  it('should delete from the global book a name that came from it', async () => {
    const wrapper = createWrapper(AddressNamePriority.GLOBAL_ADDRESSBOOK);

    await wrapper.find('[data-testid=address-delete]').trigger('click');
    await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');
    await flushPromises();

    expect(locations).toEqual(['global']);
  });

  it('should go back to the trash button, deleting nothing, when the question is cancelled', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=address-delete]').trigger('click');
    await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');

    expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=address-delete]').exists()).toBe(true);
    expect(deleteEntry).not.toHaveBeenCalled();
  });
});
