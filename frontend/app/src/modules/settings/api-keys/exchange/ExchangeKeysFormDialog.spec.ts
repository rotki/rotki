import type { ExchangeFormData } from '@/modules/balances/types/exchanges';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import ExchangeKeysFormDialog from '@/modules/settings/api-keys/exchange/ExchangeKeysFormDialog.vue';
import '@test/i18n';

/**
 * The dialog owns the save: it decides whether a rename is really a rename, which failures belong
 * on a field and which become a message, and when the caller is told an exchange was added. None of
 * that was covered, and the form's `validate()` contract is about to change under it.
 */
const { setMessage, setupExchange, validate } = vi.hoisted(() => ({
  setMessage: vi.fn(),
  setupExchange: vi.fn(),
  validate: vi.fn(),
}));

vi.mock('@/modules/balances/exchanges/use-exchanges', () => ({
  useExchanges: (): Record<string, unknown> => ({ setupExchange }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
}));

// Stubbed down to the seam the dialog uses: the exposed `validate` and the two models it writes.
vi.mock('@/modules/settings/api-keys/exchange/ExchangeKeysForm.vue', async () => {
  const { defineComponent, h } = await import('vue');
  return {
    default: defineComponent({
      emits: ['update:modelValue', 'update:stateUpdated', 'update:errorMessages'],
      name: 'ExchangeKeysForm',
      props: {
        errorMessages: { default: () => ({}), type: Object },
        modelValue: { required: true, type: Object },
        stateUpdated: { default: false, type: Boolean },
      },
      setup: (_props, { expose }) => {
        expose({ validate });
        return (): VNode => h('div', { class: 'exchange-keys-form' });
      },
    }),
  };
});

const BigDialogStub = defineComponent({
  emits: ['confirm', 'cancel'],
  name: 'BigDialog',
  setup: (_props, { slots }) => (): VNode => h('div', slots.default?.()),
});

function exchange(overrides: Partial<ExchangeFormData> = {}): ExchangeFormData {
  return {
    apiKey: 'key',
    apiSecret: 'secret',
    binanceMarkets: [],
    location: 'kucoin',
    mode: 'add',
    name: 'Kucoin 1',
    passphrase: '',
    ...overrides,
  };
}

describe('settings/api-keys/exchange/ExchangeKeysFormDialog.vue', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof ExchangeKeysFormDialog>>;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    setMessage.mockReset();
    setupExchange.mockReset().mockResolvedValue(true);
    validate.mockReset().mockReturnValue(true);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  function createWrapper(modelValue: ExchangeFormData | undefined): VueWrapper<InstanceType<typeof ExchangeKeysFormDialog>> {
    wrapper = mount(ExchangeKeysFormDialog, {
      global: {
        plugins: [pinia],
        stubs: { BigDialog: BigDialogStub, Teleport: true },
      },
      props: { modelValue },
    });
    return wrapper;
  }

  /** Saving goes through the dialog's confirm action, which also covers that it is wired up. */
  async function save(modelValue: ExchangeFormData): Promise<void> {
    createWrapper(modelValue);
    wrapper.findComponent(BigDialogStub).vm.$emit('confirm');
    await flushPromises();
  }

  it('should not save a form that does not validate', async () => {
    validate.mockReturnValue(false);

    await save(exchange());

    expect(setupExchange).not.toHaveBeenCalled();
  });

  it('should save a form that validates', async () => {
    await save(exchange());

    expect(setupExchange).toHaveBeenCalledOnce();
  });

  describe('the rename', () => {
    /**
     * The backend reads `newName` as a rename request, so sending the unchanged name would ask it
     * to rename the exchange to what it is already called.
     */
    it('should not send a rename when the name is unchanged', async () => {
      await save(exchange({ mode: 'edit', name: 'Kucoin 1', newName: 'Kucoin 1' }));

      expect(setupExchange).toHaveBeenCalledWith(expect.objectContaining({ newName: undefined }));
    });

    it('should send a rename when the name changed', async () => {
      await save(exchange({ mode: 'edit', name: 'Kucoin 1', newName: 'Kucoin 2' }));

      expect(setupExchange).toHaveBeenCalledWith(expect.objectContaining({ newName: 'Kucoin 2' }));
    });
  });

  describe('reporting a failure', () => {
    it('should put field errors back on the form', async () => {
      const error = new ApiValidationError(JSON.stringify({ apiKey: ['bad key'] }));
      setupExchange.mockRejectedValue(error);

      await save(exchange());

      expect(wrapper.findComponent({ name: 'ExchangeKeysForm' }).props('errorMessages'))
        .toMatchObject({ apiKey: ['bad key'] });
      expect(setMessage).not.toHaveBeenCalled();
    });

    it('should surface anything else as a message', async () => {
      setupExchange.mockRejectedValue(new Error('the exchange is unreachable'));

      await save(exchange());

      expect(setMessage).toHaveBeenCalledOnce();
    });

    it('should keep the dialog open when the save failed', async () => {
      setupExchange.mockResolvedValue(false);

      await save(exchange());

      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
    });
  });

  describe('after a successful save', () => {
    it('should announce an exchange that was added', async () => {
      await save(exchange({ location: 'kucoin', name: 'Kucoin 1' }));

      expect(wrapper.emitted('added')?.at(-1)?.[0]).toStrictEqual({
        location: 'kucoin',
        name: 'Kucoin 1',
      });
    });

    it('should not announce one that was only edited', async () => {
      await save(exchange({ mode: 'edit', newName: 'Kucoin 2' }));

      expect(wrapper.emitted('added')).toBeUndefined();
    });

    it('should close the dialog', async () => {
      await save(exchange());

      expect(wrapper.emitted('update:modelValue')?.at(-1)).toStrictEqual([undefined]);
    });
  });
});
