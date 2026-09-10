import { Priority, Severity } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, type VNode } from 'vue';
import AddressBookManagementMore from '@/modules/accounts/address-book/AddressBookManagementMore.vue';

const { importAddressBook, notify, removeFile } = vi.hoisted(() => ({
  importAddressBook: vi.fn<(file: File) => Promise<number>>(async () => 0),
  notify: vi.fn(),
  removeFile: vi.fn(),
}));

vi.mock('@/modules/accounts/address-book/use-address-book-import', () => ({
  useAddressBookImport: (): Record<string, unknown> => ({ importAddressBook }),
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: (): Record<string, unknown> => ({ notify }),
}));

vi.mock('@/modules/user-data/FileUpload.vue', async () => {
  const { defineComponent, h } = await import('vue');
  return {
    __esModule: true,
    default: defineComponent({
      emits: ['update:modelValue'],
      name: 'FileUpload',
      props: { modelValue: { default: undefined, type: Object } },
      setup(_props, { expose }): () => VNode {
        expose({ removeFile });
        return () => h('div');
      },
    }),
  };
});

const MenuStub = defineComponent({
  template: '<div><slot name="activator" :attrs="{}" /><slot /></div>',
});

function createWrapper(): VueWrapper<any> {
  return mount(AddressBookManagementMore, {
    global: {
      stubs: {
        ExternalLink: true,
        RuiCard: { template: '<div><slot name="header" /><slot /><slot name="footer" /></div>' },
        RuiDialog: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' },
        RuiMenu: MenuStub,
      },
    },
  });
}

function button(wrapper: VueWrapper<any>, id: string): VueWrapper<any> {
  const found = wrapper
    .findAllComponents({ name: 'RuiButton' })
    .find(item => item.attributes('data-testid') === id);
  assert(found);
  return found;
}

const CSV = new File(['address,name'], 'address-book.csv', { type: 'text/csv' });

async function importFile(wrapper: VueWrapper<any>): Promise<void> {
  await button(wrapper, 'address-book-import').trigger('click');
  wrapper.findComponent({ name: 'FileUpload' }).vm.$emit('update:modelValue', CSV);
  await nextTick();
  await button(wrapper, 'address-book-import-confirm').trigger('click');
  await flushPromises();
}

describe('addressBookManagementMore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    importAddressBook.mockResolvedValue(0);
  });

  it('should refuse to import while no file is chosen', async () => {
    const wrapper = createWrapper();

    await button(wrapper, 'address-book-import').trigger('click');

    expect(button(wrapper, 'address-book-import-confirm').props('disabled')).toBe(true);
  });

  it('should import the chosen file', async () => {
    importAddressBook.mockResolvedValue(3);
    const wrapper = createWrapper();

    await importFile(wrapper);

    expect(importAddressBook).toHaveBeenCalledWith(CSV);
  });

  /** The table behind the dialog is now stale whatever the import did, so it is always reloaded. */
  describe('once the import is done', () => {
    it('should ask for a reload after entries were added', async () => {
      importAddressBook.mockResolvedValue(3);
      const wrapper = createWrapper();

      await importFile(wrapper);

      expect(wrapper.emitted('refresh')).toHaveLength(1);
    });

    it('should ask for a reload even when nothing was added', async () => {
      const wrapper = createWrapper();

      await importFile(wrapper);

      expect(wrapper.emitted('refresh')).toHaveLength(1);
    });

    /** An import that added nothing has nothing to announce. */
    it('should say how many entries were added', async () => {
      importAddressBook.mockResolvedValue(3);
      const wrapper = createWrapper();

      await importFile(wrapper);

      expect(notify).toHaveBeenCalledWith({
        message: 'address_book.import.import_success.message::3',
        priority: Priority.HIGH,
        severity: Severity.INFO,
        title: 'address_book.import.title',
      });
    });

    it('should stay quiet when nothing was added', async () => {
      const wrapper = createWrapper();

      await importFile(wrapper);

      expect(notify).not.toHaveBeenCalled();
    });

    it('should forget the file so it is not offered again', async () => {
      const wrapper = createWrapper();
      await importFile(wrapper);

      await button(wrapper, 'address-book-import').trigger('click');

      expect(button(wrapper, 'address-book-import-confirm').props('disabled')).toBe(true);
    });
  });

  it('should import nothing on cancel', async () => {
    const wrapper = createWrapper();
    await button(wrapper, 'address-book-import').trigger('click');

    await button(wrapper, 'address-book-import-cancel').trigger('click');

    expect(importAddressBook).not.toHaveBeenCalled();
    expect(wrapper.emitted('refresh')).toBeUndefined();
  });
});
