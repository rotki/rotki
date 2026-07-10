import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';

const { flushMock, useSettingModelMock } = vi.hoisted(() => ({ flushMock: vi.fn(), useSettingModelMock: vi.fn() }));
vi.mock('@/modules/settings/use-setting-model', () => ({ useSettingModel: useSettingModelMock }));

const RuiTextFieldStub = {
  props: ['modelValue', 'successMessages', 'errorMessages', 'label'],
  emits: ['update:model-value'],
  template: `<div>
    <span class="model">{{ modelValue }}</span>
    <span class="success">{{ successMessages }}</span>
    <span class="error">{{ errorMessages }}</span>
  </div>`,
};

const ResetStub = {
  emits: ['confirm'],
  template: `<button class="reset" @click="$emit('confirm')" />`,
};

describe('settingNumber', () => {
  let model: Ref<number>;
  let error: Ref<string>;
  let success: Ref<boolean>;

  function createWrapper(props: Record<string, unknown> = {}): VueWrapper {
    return mount(SettingNumber, {
      props: { setting: 'balanceSaveFrequency', label: 'Frequency', ...props },
      global: {
        stubs: { RuiTextField: RuiTextFieldStub, SettingResetConfirmButton: ResetStub },
      },
    });
  }

  beforeEach(() => {
    flushMock.mockClear();
    model = ref<number>(3);
    error = ref<string>('');
    success = ref<boolean>(false);
    useSettingModelMock.mockReturnValue({ error, flush: flushMock, model, pending: ref(false), success });
  });

  it('should render the field with the current value', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.model').text()).toBe('3');
  });

  it('should persist a valid value as a number', async () => {
    const wrapper = createWrapper({ min: 1, max: 20 });
    await wrapper.findComponent(RuiTextFieldStub).vm.$emit('update:model-value', '15');
    await nextTick();
    expect(get(model)).toBe(15);
  });

  it('should not persist a value below the minimum', async () => {
    const wrapper = createWrapper({ min: 1, max: 20 });
    await wrapper.findComponent(RuiTextFieldStub).vm.$emit('update:model-value', '0');
    await nextTick();
    expect(get(model)).toBe(3);
    expect(wrapper.find('.error').text()).not.toBe('');
  });

  it('should show a saved message after a successful write', async () => {
    const wrapper = createWrapper();
    set(success, true);
    await nextTick();
    expect(wrapper.find('.success').text()).not.toBe('');
  });

  it('should reset to the default and flush immediately', async () => {
    const wrapper = createWrapper({ default: 10, min: 1, max: 20 });
    await wrapper.find('.reset').trigger('click');
    await nextTick();
    expect(get(model)).toBe(10);
    expect(flushMock).toHaveBeenCalledOnce();
  });

  it('should not render a reset button without a default', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.reset').exists()).toBe(false);
  });

  it('should prefix a callback error message on a failed write', async () => {
    const wrapper = createWrapper({ errorMessage: (value: number) => `bad ${value}` });
    set(error, 'boom');
    await nextTick();
    expect(wrapper.find('.error').text()).toContain('bad 3');
  });
});
