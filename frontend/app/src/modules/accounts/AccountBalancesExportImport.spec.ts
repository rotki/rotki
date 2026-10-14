import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import AccountBalancesExportImport from '@/modules/accounts/AccountBalancesExportImport.vue';

const { exportAccounts, importAccounts } = vi.hoisted(() => ({
  exportAccounts: vi.fn(),
  importAccounts: vi.fn(async () => {}),
}));

vi.mock('@/modules/accounts/import-export/use-account-import-export', () => ({
  useAccountImportExport: (): Record<string, unknown> => ({ exportAccounts, importAccounts }),
}));

const MenuStub = defineComponent({
  template: '<div><slot name="activator" :attrs="{}" /><slot /></div>',
});

/** Stands in for the library uploader: it only holds the chosen file through its model. */
const FileUploadStub = defineComponent({
  emits: ['update:modelValue'],
  name: 'RuiFileUpload',
  props: { modelValue: { default: undefined, type: Object } },
  template: '<div />',
});

function createWrapper(): VueWrapper<any> {
  return mount(AccountBalancesExportImport, {
    global: {
      stubs: {
        ExternalLink: true,
        RuiCard: { template: '<div><slot name="header" /><slot /><slot name="footer" /></div>' },
        RuiDialog: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' },
        RuiFileUpload: FileUploadStub,
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

function uploader(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent({ name: 'RuiFileUpload' });
}

const CSV = new File(['address,chain'], 'accounts.csv', { type: 'text/csv' });

async function openImport(wrapper: VueWrapper<any>): Promise<void> {
  await button(wrapper, 'accounts-import').trigger('click');
}

async function choose(wrapper: VueWrapper<any>, file: File): Promise<void> {
  uploader(wrapper).vm.$emit('update:modelValue', file);
  await nextTick();
}

describe('accountBalancesExportImport', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should export on request', async () => {
    const wrapper = createWrapper();

    await button(wrapper, 'accounts-export').trigger('click');

    expect(exportAccounts).toHaveBeenCalledTimes(1);
  });

  describe('importing', () => {
    it('should stay closed until it is asked for', () => {
      expect(uploader(createWrapper()).exists()).toBe(false);
    });

    it('should open on request', async () => {
      const wrapper = createWrapper();

      await openImport(wrapper);

      expect(uploader(wrapper).exists()).toBe(true);
    });

    /** There is nothing to import until a file has been chosen. */
    it('should refuse to import while no file is chosen', async () => {
      const wrapper = createWrapper();
      await openImport(wrapper);

      expect(button(wrapper, 'accounts-import-confirm').props('disabled')).toBe(true);
    });

    it('should offer the import once a file is chosen', async () => {
      const wrapper = createWrapper();
      await openImport(wrapper);

      await choose(wrapper, CSV);

      expect(button(wrapper, 'accounts-import-confirm').props('disabled')).toBe(false);
    });

    it('should import the chosen file', async () => {
      const wrapper = createWrapper();
      await openImport(wrapper);
      await choose(wrapper, CSV);

      await button(wrapper, 'accounts-import-confirm').trigger('click');
      await flushPromises();

      expect(importAccounts).toHaveBeenCalledWith(CSV);
    });

    /** The dialog closes on the way in, so the import runs against the page rather than over it. */
    it('should close before the import runs', async () => {
      const wrapper = createWrapper();
      await openImport(wrapper);
      await choose(wrapper, CSV);

      await button(wrapper, 'accounts-import-confirm').trigger('click');
      await flushPromises();

      expect(uploader(wrapper).exists()).toBe(false);
    });

    /** Reopening the dialog after an import must not offer the file that was already imported. */
    it('should forget the file once the import is done', async () => {
      const wrapper = createWrapper();
      await openImport(wrapper);
      await choose(wrapper, CSV);
      await button(wrapper, 'accounts-import-confirm').trigger('click');
      await flushPromises();

      await openImport(wrapper);

      expect(uploader(wrapper).props('modelValue')).toBeUndefined();
      expect(button(wrapper, 'accounts-import-confirm').props('disabled')).toBe(true);
    });

    it('should leave the dialog alone on cancel', async () => {
      const wrapper = createWrapper();
      await openImport(wrapper);

      await button(wrapper, 'accounts-import-cancel').trigger('click');

      expect(uploader(wrapper).exists()).toBe(false);
      expect(importAccounts).not.toHaveBeenCalled();
    });
  });
});
