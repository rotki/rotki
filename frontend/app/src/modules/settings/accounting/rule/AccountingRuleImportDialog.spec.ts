import type { ActionStatus } from '@/modules/core/common/action';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import AccountingRuleImportDialog from '@/modules/settings/accounting/rule/AccountingRuleImportDialog.vue';

const { spies } = vi.hoisted(() => ({
  spies: {
    importJSON: vi.fn<(file: File) => Promise<ActionStatus | null>>(),
  },
}));

vi.mock('@/modules/settings/accounting/use-accounting-settings', () => ({
  useAccountingSettings: (): object => ({ importJSON: spies.importJSON }),
}));

const FileUploadStub = defineComponent({
  name: 'RuiFileUpload',
  props: {
    errorMessages: { default: (): string[] => [], type: Array },
    modelValue: { default: undefined, type: File },
  },
  emits: ['update:modelValue', 'error'],
  template: '<div />',
});

const CONFIRM = '[data-testid=accounting-rule-import-confirm]';

describe('accountingRuleImportDialog', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof AccountingRuleImportDialog>>;
  const file = new File(['{}'], 'rules.json', { type: 'application/json' });

  function createWrapper(): VueWrapper<InstanceType<typeof AccountingRuleImportDialog>> {
    return mount(AccountingRuleImportDialog, {
      global: {
        plugins: [pinia],
        stubs: {
          RuiDialog: { template: '<div><slot /></div>' },
          RuiFileUpload: FileUploadStub,
        },
      },
      props: { loading: false, modelValue: true },
    });
  }

  function upload(): VueWrapper<InstanceType<typeof FileUploadStub>> {
    return wrapper.findComponent(FileUploadStub);
  }

  async function chooseFile(): Promise<void> {
    upload().vm.$emit('update:modelValue', file);
    await nextTick();
  }

  async function importChosenFile(): Promise<void> {
    await wrapper.find(CONFIRM).trigger('click');
    await flushPromises();
  }

  beforeEach(() => {
    vi.clearAllMocks();
    pinia = createCustomPinia();
    setActivePinia(pinia);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should not offer the import until a file is chosen', async () => {
    wrapper = createWrapper();

    expect(wrapper.find(CONFIRM).attributes('disabled')).toBeDefined();

    await chooseFile();

    expect(wrapper.find(CONFIRM).attributes('disabled')).toBeUndefined();
  });

  describe('on success', () => {
    beforeEach(() => {
      spies.importJSON.mockResolvedValue({ success: true });
    });

    it('should import the chosen file and report it imported', async () => {
      wrapper = createWrapper();
      await chooseFile();

      await importChosenFile();

      expect(spies.importJSON).toHaveBeenCalledExactlyOnceWith(file);
      expect(useMessageStore().message).toMatchObject({
        description: 'actions.accounting_rules.import.message.success',
        success: true,
        title: 'actions.accounting_rules.import.title',
      });
    });

    it('should close, drop the file and ask the rules to reload', async () => {
      wrapper = createWrapper();
      await chooseFile();

      await importChosenFile();

      expect(wrapper.emitted('update:modelValue')).toEqual([[false]]);
      expect(wrapper.emitted('refresh')).toHaveLength(1);
      expect(upload().props('modelValue')).toBeUndefined();
    });
  });

  describe('on failure', () => {
    it('should show why on the field and stay open with the file', async () => {
      spies.importJSON.mockResolvedValue({ message: 'rule 3 is invalid', success: false });
      wrapper = createWrapper();
      await chooseFile();

      await importChosenFile();

      expect(upload().props('errorMessages')).toEqual(['actions.accounting_rules.import.message.failure::rule 3 is invalid']);
      expect(useMessageStore().message).toBeUndefined();
      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
      expect(wrapper.emitted('refresh')).toBeUndefined();
      expect(upload().props('modelValue')?.name).toBe('rules.json');
    });

    it('should clear the error once another file is chosen', async () => {
      spies.importJSON.mockResolvedValue({ message: 'rule 3 is invalid', success: false });
      wrapper = createWrapper();
      await chooseFile();
      await importChosenFile();

      await chooseFile();

      expect(upload().props('errorMessages')).toEqual([]);
    });

    it('should say nothing when the import was not attempted', async () => {
      spies.importJSON.mockResolvedValue(null);
      wrapper = createWrapper();
      await chooseFile();

      await importChosenFile();

      expect(spies.importJSON).toHaveBeenCalledOnce();
      expect(useMessageStore().message).toBeUndefined();
      expect(upload().props('errorMessages')).toEqual([]);
      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
    });
  });

  it('should close without importing on cancel', async () => {
    wrapper = createWrapper();
    await chooseFile();

    await wrapper.find('[data-testid=accounting-rule-import-cancel]').trigger('click');

    expect(wrapper.emitted('update:modelValue')).toEqual([[false]]);
    expect(spies.importJSON).not.toHaveBeenCalled();
  });
});
