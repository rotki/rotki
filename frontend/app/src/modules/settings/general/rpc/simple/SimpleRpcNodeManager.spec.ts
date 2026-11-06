import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, type VNode } from 'vue';
import SimpleRpcNodeManager from '@/modules/settings/general/rpc/simple/SimpleRpcNodeManager.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';
import '@test/i18n';

const { readSetting, write } = vi.hoisted(() => ({
  readSetting: vi.fn(),
  write: vi.fn(),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: readSetting,
}));

vi.mock('@/modules/settings/settings-writer', () => ({
  useSettingsWriter: (): Record<string, unknown> => ({ write }),
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

  describe('deleting the endpoint', () => {
    beforeEach(() => {
      readSetting.mockReturnValue(ref<string>('https://rpc.polkadot.io'));
    });

    it('should have the row ask before deleting, and write nothing until confirmed', async () => {
      wrapper = createWrapper();
      await nextTick();

      expect(wrapper.findComponent(RowActions).props('deleteConfirm')).toEqual({
        message: 'general_settings.simple_node_setting.delete_confirmation.subtitle',
        title: 'general_settings.simple_node_setting.delete_confirmation.title',
      });
      expect(write).not.toHaveBeenCalled();
    });

    it('should clear the setting once the question is confirmed, without opening the dialog', async () => {
      write.mockResolvedValue({ success: true });
      wrapper = createWrapper();
      await nextTick();

      wrapper.findComponent(RowActions).vm.$emit('delete-click');
      await flushPromises();

      expect(write).toHaveBeenCalledWith('dotRpcEndpoint', '');
      expect(wrapper.find('.big-dialog').attributes('data-display')).toBe('false');
      expect(wrapper.find('[data-testid=simple-node-delete-error]').exists()).toBe(false);
    });

    it('should name a failed delete above the table, with no retry of its own', async () => {
      write.mockResolvedValue({ message: 'node is in use', success: false });
      wrapper = createWrapper();
      await nextTick();

      wrapper.findComponent(RowActions).vm.$emit('delete-click');
      await flushPromises();

      const strip = wrapper.find('[data-testid=simple-node-delete-error]');
      expect(strip.text()).toContain('node is in use');
      expect(strip.text()).toContain('general_settings.simple_node_setting.delete_error');
      expect(strip.find('[data-testid=failure-strip-retry]').exists()).toBe(false);
    });

    it('should drop the failure once a later delete succeeds', async () => {
      write.mockResolvedValueOnce({ message: 'node is in use', success: false });
      write.mockResolvedValueOnce({ success: true });
      wrapper = createWrapper();
      await nextTick();

      wrapper.findComponent(RowActions).vm.$emit('delete-click');
      await flushPromises();
      wrapper.findComponent(RowActions).vm.$emit('delete-click');
      await flushPromises();

      expect(wrapper.find('[data-testid=simple-node-delete-error]').exists()).toBe(false);
    });
  });
});
