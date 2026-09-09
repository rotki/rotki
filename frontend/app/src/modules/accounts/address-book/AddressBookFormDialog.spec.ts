import type { AddressBookPayload } from '@/modules/accounts/address-book/eth-names';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { defineComponent, h, nextTick, type VNode } from 'vue';
import AddressBookFormDialog from '@/modules/accounts/address-book/AddressBookFormDialog.vue';
import { ApiValidationError } from '@/modules/core/api/types/errors';

const { addAddressBook, setMessage, updateAddressBook } = vi.hoisted(() => ({
  addAddressBook: vi.fn(),
  setMessage: vi.fn(),
  updateAddressBook: vi.fn(),
}));

vi.mock('@/modules/accounts/address-book/use-address-book-operations', () => ({
  useAddressBookOperations: (): Record<string, Mock> => ({ addAddressBook, updateAddressBook }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, Mock> => ({ setMessage }),
}));

const validate = vi.fn(async () => true);

/** The dialog validates through a template ref, so the stub has to expose the method it calls. */
const FormStub = defineComponent({
  name: 'AddressBookForm',
  props: ['modelValue', 'errorMessages', 'stateUpdated', 'editMode'],
  setup(_, { expose }): () => VNode {
    expose({ validate });
    return () => h('div');
  },
});

/** `BigDialog` teleports and owns the footer buttons; the two here stand for confirm and cancel. */
const BigDialogStub = {
  emits: ['confirm', 'cancel'],
  name: 'BigDialog',
  props: ['title', 'display', 'action', 'loading', 'promptOnClose'],
  template: `<div>
    <slot />
    <button data-testid="stub-confirm" @click="$emit('confirm')" />
    <button data-testid="stub-cancel" @click="$emit('cancel')" />
  </div>`,
};

function entry(overrides: Partial<AddressBookPayload> = {}): AddressBookPayload {
  return { address: '0xabc', blockchain: 'eth', location: 'private', name: 'wallet', ...overrides };
}

function createWrapper(props: Record<string, unknown> = {}): VueWrapper<any> {
  return mount(AddressBookFormDialog, {
    global: {
      stubs: {
        AddressBookForm: FormStub,
        BigDialog: BigDialogStub,
      },
    },
    props: { open: true, ...props },
  });
}

/** The dialog as the management page opens it to change an entry that already exists. */
function editing(overrides: Partial<AddressBookPayload> = {}): VueWrapper<any> {
  return createWrapper({ editMode: true, editableItem: entry(overrides) });
}

async function confirm(wrapper: VueWrapper<any>): Promise<void> {
  await wrapper.find('[data-testid=stub-confirm]').trigger('click');
  await flushPromises();
}

function formValue(wrapper: VueWrapper<any>): AddressBookPayload {
  return wrapper.findComponent(FormStub).props('modelValue');
}

describe('addressBookFormDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    validate.mockResolvedValue(true);
    addAddressBook.mockResolvedValue(true);
    updateAddressBook.mockResolvedValue(true);
  });

  describe('seeding the form', () => {
    it('should start empty when nothing was handed over', () => {
      const wrapper = createWrapper();

      expect(formValue(wrapper)).toEqual({ address: '', blockchain: 'all', location: 'private', name: '' });
    });

    it('should preselect the chain the caller was showing', () => {
      const wrapper = createWrapper({ selectedChain: 'optimism' });

      expect(formValue(wrapper).blockchain).toBe('optimism');
    });

    it('should open in the location the caller was showing', () => {
      const wrapper = createWrapper({ location: 'global' });

      expect(formValue(wrapper).location).toBe('global');
    });

    it('should load the entry handed over', () => {
      const wrapper = editing({ name: 'exchange' });

      expect(formValue(wrapper).name).toBe('exchange');
    });

    /** An entry saved for every chain has no blockchain; the picker shows that as `all`. */
    it('should show an entry without a chain as covering all of them', () => {
      const wrapper = editing({ blockchain: null });

      expect(formValue(wrapper).blockchain).toBe('all');
    });

    it('should discard the form once the dialog is closed', async () => {
      const wrapper = editing();

      await wrapper.setProps({ open: false });

      expect(wrapper.findComponent(FormStub).exists()).toBe(false);
    });
  });

  describe('the heading', () => {
    it('should announce an edit when the entry is being updated', () => {
      expect(editing().findComponent(BigDialogStub).props('title')).toBe('address_book.dialog.edit_title');
    });

    /**
     * The messages dialog seeds the form with the address the backend asked the user to name, and
     * that is an addition however filled-in the form arrives.
     */
    it('should announce an addition when a seeded entry is being added', () => {
      const wrapper = createWrapper({ editableItem: entry() });

      expect(wrapper.findComponent(BigDialogStub).props('title')).toBe('address_book.dialog.add_title');
    });
  });

  describe('saving', () => {
    it('should not save a form that does not validate', async () => {
      validate.mockResolvedValue(false);
      const wrapper = createWrapper();

      await confirm(wrapper);

      expect(addAddressBook).not.toHaveBeenCalled();
      expect(updateAddressBook).not.toHaveBeenCalled();
    });

    it('should add an entry the dialog was not told to update', async () => {
      const wrapper = createWrapper({ root: true });

      await confirm(wrapper);

      expect(addAddressBook).toHaveBeenCalledWith('private', [{ address: '', blockchain: null, name: '' }], true);
    });

    it('should add a seeded entry rather than update it', async () => {
      const wrapper = createWrapper({ editableItem: entry() });

      await confirm(wrapper);

      expect(addAddressBook).toHaveBeenCalledTimes(1);
      expect(updateAddressBook).not.toHaveBeenCalled();
    });

    it('should update the entry when told to', async () => {
      const wrapper = editing();

      await confirm(wrapper);

      expect(updateAddressBook).toHaveBeenCalledWith('private', [{
        address: '0xabc',
        blockchain: 'eth',
        name: 'wallet',
      }]);
      expect(addAddressBook).not.toHaveBeenCalled();
    });

    it('should trim the address and the name', async () => {
      const wrapper = editing({ address: '  0xabc  ', name: '  wallet  ' });

      await confirm(wrapper);

      expect(updateAddressBook).toHaveBeenCalledWith('private', [{
        address: '0xabc',
        blockchain: 'eth',
        name: 'wallet',
      }]);
    });

    /** `all` is the picker's word for every chain, which the backend spells as no chain at all. */
    it('should send no chain for an entry covering all of them', async () => {
      const wrapper = editing({ blockchain: null });

      await confirm(wrapper);

      expect(updateAddressBook).toHaveBeenCalledWith('private', [expect.objectContaining({ blockchain: null })]);
    });
  });

  describe('after a successful save', () => {
    it('should close the dialog and ask for a refresh', async () => {
      const wrapper = editing();

      await confirm(wrapper);

      expect(wrapper.emitted('update:open')?.at(-1)).toEqual([false]);
      expect(wrapper.emitted('refresh')).toHaveLength(1);
    });

    it('should switch to the tab the entry was saved into', async () => {
      const wrapper = createWrapper({ editMode: true, editableItem: entry({ location: 'global' }) });

      await confirm(wrapper);

      expect(wrapper.emitted('update:tab')?.[0]).toEqual([0]);
    });

    it('should switch to the private tab for a private entry', async () => {
      const wrapper = editing();

      await confirm(wrapper);

      expect(wrapper.emitted('update:tab')?.[0]).toEqual([1]);
    });
  });

  describe('after a rejected save', () => {
    it('should keep the dialog open', async () => {
      updateAddressBook.mockResolvedValue(false);
      const wrapper = editing();

      await confirm(wrapper);

      expect(wrapper.emitted('update:open')).toBeUndefined();
      expect(wrapper.emitted('refresh')).toBeUndefined();
    });

    it('should mark the offending fields when the backend named them', async () => {
      updateAddressBook.mockRejectedValue(new ApiValidationError(JSON.stringify({ address: ['not an address'] })));
      const wrapper = editing();

      await confirm(wrapper);

      expect(wrapper.findComponent(FormStub).props('errorMessages')).toEqual({ address: ['not an address'] });
      expect(setMessage).not.toHaveBeenCalled();
    });

    it('should surface an error that names no field', async () => {
      updateAddressBook.mockRejectedValue(new Error('the backend said no'));
      const wrapper = editing();

      await confirm(wrapper);

      expect(setMessage).toHaveBeenCalledWith({
        description: 'address_book.actions.edit.error.description::the backend said no',
        success: false,
        title: 'address_book.actions.edit.error.title',
      });
    });

    it('should word the error as an addition when the entry is new', async () => {
      addAddressBook.mockRejectedValue(new Error('the backend said no'));

      await confirm(createWrapper());

      expect(setMessage).toHaveBeenCalledWith({
        description: 'address_book.actions.add.error.description::the backend said no',
        success: false,
        title: 'address_book.actions.add.error.title',
      });
    });
  });

  /** The errors belong to the chain they were reported for, so switching chains retires them. */
  describe('the field errors', () => {
    async function rejectedWrapper(): Promise<VueWrapper<any>> {
      updateAddressBook.mockRejectedValue(new ApiValidationError(JSON.stringify({ address: ['not an address'] })));
      const wrapper = editing();
      await confirm(wrapper);
      return wrapper;
    }

    it('should be cleared when the chain changes', async () => {
      const wrapper = await rejectedWrapper();

      wrapper.findComponent(FormStub).vm.$emit('update:modelValue', entry({ blockchain: 'optimism' }));
      await nextTick();

      expect(wrapper.findComponent(FormStub).props('errorMessages')).toEqual({});
    });

    it('should survive an edit that leaves the chain alone', async () => {
      const wrapper = await rejectedWrapper();

      wrapper.findComponent(FormStub).vm.$emit('update:modelValue', entry({ name: 'renamed' }));
      await nextTick();

      expect(wrapper.findComponent(FormStub).props('errorMessages')).toEqual({ address: ['not an address'] });
    });
  });

  it('should close without saving when dismissed', async () => {
    const wrapper = editing();

    await wrapper.find('[data-testid=stub-cancel]').trigger('click');

    expect(wrapper.emitted('update:open')?.at(-1)).toEqual([false]);
    expect(updateAddressBook).not.toHaveBeenCalled();
  });
});
