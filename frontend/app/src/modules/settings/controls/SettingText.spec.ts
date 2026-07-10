import { mount, type VueWrapper } from '@vue/test-utils';
import { helpers } from '@vuelidate/validators';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import SettingText from '@/modules/settings/controls/SettingText.vue';

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

describe('settingText', () => {
  let model: Ref<string>;
  let error: Ref<string>;
  let success: Ref<boolean>;

  function createWrapper(props: Record<string, unknown> = {}): VueWrapper {
    return mount(SettingText, {
      props: { setting: 'csvExportDelimiter', label: 'Delimiter', ...props },
      global: {
        stubs: { RuiTextField: RuiTextFieldStub, SettingResetConfirmButton: ResetStub },
      },
    });
  }

  beforeEach(() => {
    flushMock.mockClear();
    model = ref<string>(',');
    error = ref<string>('');
    success = ref<boolean>(false);
    useSettingModelMock.mockReturnValue({ error, flush: flushMock, model, pending: ref(false), success });
  });

  it('should render the field with the current value', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.model').text()).toBe(',');
  });

  it('should persist a valid value', async () => {
    const wrapper = createWrapper({ maxLength: 1, required: true });
    await wrapper.findComponent(RuiTextFieldStub).vm.$emit('update:model-value', ';');
    await nextTick();
    expect(get(model)).toBe(';');
  });

  it('should not persist a value that exceeds maxLength', async () => {
    const wrapper = createWrapper({ maxLength: 1, required: true });
    await wrapper.findComponent(RuiTextFieldStub).vm.$emit('update:model-value', ';;');
    await nextTick();
    expect(get(model)).toBe(',');
    expect(wrapper.find('.error').text()).not.toBe('');
  });

  it('should gate on a custom rules escape hatch', async () => {
    const rules = { value: { onlyDash: helpers.withMessage('dash only', (v: string) => v === '-') } };
    const wrapper = createWrapper({ rules });
    await wrapper.findComponent(RuiTextFieldStub).vm.$emit('update:model-value', 'x');
    await nextTick();
    expect(get(model)).toBe(',');
    await wrapper.findComponent(RuiTextFieldStub).vm.$emit('update:model-value', '-');
    await nextTick();
    expect(get(model)).toBe('-');
  });

  it('should reset to the default and flush immediately', async () => {
    const wrapper = createWrapper({ default: '.', maxLength: 1, required: true });
    await wrapper.find('.reset').trigger('click');
    await nextTick();
    expect(get(model)).toBe('.');
    expect(flushMock).toHaveBeenCalledOnce();
  });
});
