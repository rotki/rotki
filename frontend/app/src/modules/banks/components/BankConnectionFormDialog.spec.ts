import type { BankFormData } from '@/modules/banks/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import BankConnectionFormDialog from '@/modules/banks/components/BankConnectionFormDialog.vue';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import '@test/i18n';

const { setMessage, setupBank, validate } = vi.hoisted(() => ({
  setMessage: vi.fn(),
  setupBank: vi.fn(),
  validate: vi.fn(),
}));

vi.mock('@/modules/banks/use-banks', () => ({
  useBanks: (): Record<string, unknown> => ({ setupBank }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

vi.mock('@/modules/banks/components/BankConnectionForm.vue', () => ({
  default: defineComponent({
    props: { errorMessages: { default: (): Record<string, string[]> => ({}), type: Object } },
    setup(props, { expose }) {
      expose({ validate });
      return (): VNode => h('div', { 'data-testid': 'form-stub' }, JSON.stringify(props.errorMessages));
    },
  }),
}));

const BigDialogStub = defineComponent({
  emits: ['cancel', 'confirm'],
  setup: (_props, { slots }) => (): VNode => h('div', slots.default?.()),
});

function createForm(): BankFormData {
  return {
    credentials: { api_key: 'login', api_secret: 'secret' },
    location: 'qonto',
    mode: 'add',
    name: 'Qonto main',
    newName: '',
  };
}

describe('bankConnectionFormDialog', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof BankConnectionFormDialog>>;

  function createWrapper(modelValue: BankFormData | undefined): VueWrapper<InstanceType<typeof BankConnectionFormDialog>> {
    return mount(BankConnectionFormDialog, {
      global: {
        plugins: [pinia],
        stubs: { BigDialog: BigDialogStub, Teleport: true },
      },
      props: { modelValue },
    });
  }

  async function confirm(): Promise<void> {
    wrapper.findComponent(BigDialogStub).vm.$emit('confirm');
    await flushPromises();
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();
    validate.mockReturnValue(true);
  });

  it('should save the entry and emit added with the connection identity', async () => {
    setupBank.mockResolvedValue(true);
    wrapper = createWrapper(createForm());
    await confirm();
    expect(setupBank).toHaveBeenCalledWith(createForm());
    expect(wrapper.emitted('added')).toEqual([[{ location: 'qonto', name: 'Qonto main' }]]);
    expect(wrapper.emitted('update:modelValue')).toEqual([[undefined]]);
  });

  it('should not save when the form does not validate', async () => {
    validate.mockReturnValue(false);
    wrapper = createWrapper(createForm());
    await confirm();
    expect(setupBank).not.toHaveBeenCalled();
  });

  it('should map an api credential error onto the credentials field', async () => {
    setupBank.mockRejectedValue(new ApiValidationError(JSON.stringify({ api_secret: ['wrong'] })));
    wrapper = createWrapper(createForm());
    await confirm();
    expect(setMessage).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid=form-stub]').text()).toContain('"credentials.api_secret":["wrong"]');
    expect(wrapper.emitted('added')).toBeUndefined();
  });

  it('should show a message for a plain error, such as the bank rejecting the credentials', async () => {
    setupBank.mockRejectedValue(new Error('Qonto rejected the credentials'));
    wrapper = createWrapper(createForm());
    await confirm();
    expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({
      description: 'bank_settings.errors.setup_message::qonto, Qonto rejected the credentials',
    }));
  });
});
