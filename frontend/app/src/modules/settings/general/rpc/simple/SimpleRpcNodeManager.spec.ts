import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import SimpleRpcNodeManager from '@/modules/settings/general/rpc/simple/SimpleRpcNodeManager.vue';
import '@test/i18n';

const { readSetting, show, write } = vi.hoisted(() => ({
  readSetting: vi.fn(),
  show: vi.fn(),
  write: vi.fn(),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: readSetting,
}));

vi.mock('@/modules/settings/settings-writer', () => ({
  useSettingsWriter: (): Record<string, unknown> => ({ write }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): Record<string, unknown> => ({ show }),
}));

vi.mock('@/modules/settings/general/rpc/simple/SimpleRpcNodeManagerForm.vue', async () => {
  const { defineComponent, h } = await import('vue');
  return {
    default: defineComponent({
      emits: ['update:modelValue', 'update:stateUpdated', 'update:errorMessages'],
      name: 'SimpleRpcNodeManagerForm',
      props: {
        errorMessages: { default: () => ({}), type: Object },
        modelValue: { default: '', type: String },
        stateUpdated: { default: false, type: Boolean },
      },
      setup: (props, { expose }) => {
        expose({ validate: (): boolean => true });
        return (): VNode => h('div', { 'class': 'rpc-form', 'data-url': props.modelValue });
      },
    }),
  };
});

const BigDialogStub = defineComponent({
  emits: ['confirm', 'cancel'],
  name: 'BigDialog',
  props: {
    display: { default: false, type: Boolean },
  },
  setup: (props, { slots }) => (): VNode => h(
    'div',
    { 'class': 'big-dialog', 'data-display': String(props.display) },
    slots.default?.(),
  ),
});

describe('settings/general/rpc/simple/SimpleRpcNodeManager.vue', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof SimpleRpcNodeManager>>;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();
    readSetting.mockReturnValue(ref<string>(''));
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  function createWrapper(): VueWrapper<InstanceType<typeof SimpleRpcNodeManager>> {
    return mount(SimpleRpcNodeManager, {
      global: {
        plugins: [pinia],
        stubs: {
          BigDialog: BigDialogStub,
        },
      },
      props: {
        setting: 'dotRpcEndpoint',
      },
    });
  }

  it('should offer an add button when no endpoint is set', async () => {
    wrapper = createWrapper();
    await nextTick();

    expect(wrapper.find('[data-testid=add-simple-node]').exists()).toBe(true);
  });

  it('should open the dialog with an empty url when adding', async () => {
    wrapper = createWrapper();
    await nextTick();

    expect(wrapper.find('.big-dialog').attributes('data-display')).toBe('false');

    await wrapper.find('[data-testid=add-simple-node]').trigger('click');
    await nextTick();

    expect(wrapper.find('.big-dialog').attributes('data-display')).toBe('true');
    expect(wrapper.find('.rpc-form').attributes('data-url')).toBe('');
  });

  it('should save the entered url to the setting', async () => {
    write.mockResolvedValue({ success: true });
    wrapper = createWrapper();
    await nextTick();

    await wrapper.find('[data-testid=add-simple-node]').trigger('click');
    await nextTick();

    wrapper.findComponent({ name: 'SimpleRpcNodeManagerForm' }).vm.$emit('update:modelValue', 'https://rpc.polkadot.io');
    await nextTick();
    wrapper.findComponent(BigDialogStub).vm.$emit('confirm');
    await flushPromises();

    expect(write).toHaveBeenCalledWith('dotRpcEndpoint', 'https://rpc.polkadot.io');
  });

  it('should not offer an add button when an endpoint is already set', async () => {
    readSetting.mockReturnValue(ref<string>('https://rpc.polkadot.io'));
    wrapper = createWrapper();
    await nextTick();

    expect(wrapper.find('[data-testid=add-simple-node]').exists()).toBe(false);
    expect(wrapper.text()).toContain('https://rpc.polkadot.io');
  });
});
