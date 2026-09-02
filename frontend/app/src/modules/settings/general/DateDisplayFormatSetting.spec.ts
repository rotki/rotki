import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import DateDisplayFormatSetting from '@/modules/settings/general/DateDisplayFormatSetting.vue';

const { flushMock, useSettingModelMock } = vi.hoisted(() => ({ flushMock: vi.fn(), useSettingModelMock: vi.fn() }));
vi.mock('@/modules/settings/use-setting-model', () => ({ useSettingModel: useSettingModelMock }));

const RuiTextFieldStub = {
  props: ['modelValue', 'successMessages', 'errorMessages', 'label', 'hint'],
  emits: ['update:model-value'],
  template: `<div>
    <span class="model">{{ modelValue }}</span>
    <span class="success">{{ successMessages }}</span>
    <span class="error">{{ errorMessages }}</span>
    <span class="error-count">{{ Array.isArray(errorMessages) ? errorMessages.length : (errorMessages ? 1 : 0) }}</span>
    <span class="hint">{{ hint }}</span>
  </div>`,
};

const ResetStub = {
  emits: ['confirm'],
  template: `<button class="reset" @click="$emit('confirm')" />`,
};

describe('dateDisplayFormatSetting', () => {
  let model: Ref<string>;
  let error: Ref<string>;
  let success: Ref<boolean>;

  function createWrapper(): VueWrapper {
    return mount(DateDisplayFormatSetting, {
      global: {
        stubs: {
          DateFormatHelp: true,
          RuiTextField: RuiTextFieldStub,
          SettingResetConfirmButton: ResetStub,
        },
      },
    });
  }

  async function input(wrapper: VueWrapper, value: string): Promise<void> {
    await wrapper.findComponent(RuiTextFieldStub).vm.$emit('update:model-value', value);
    await nextTick();
  }

  beforeEach(() => {
    flushMock.mockClear();
    model = ref<string>('%d/%m/%Y');
    error = ref<string>('');
    success = ref<boolean>(false);
    useSettingModelMock.mockReturnValue({ error, flush: flushMock, model, pending: ref(false), success });
  });

  it('should render the field with the current value', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.model').text()).toBe('%d/%m/%Y');
  });

  it('should persist a format that contains valid directives', async () => {
    const wrapper = createWrapper();
    await input(wrapper, '%Y-%m-%d');
    expect(get(model)).toBe('%Y-%m-%d');
    expect(wrapper.find('.error-count').text()).toBe('0');
  });

  it('should not persist a format without valid directives', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 'not a format');
    expect(get(model)).toBe('%d/%m/%Y');
    expect(wrapper.find('.error').text()).toContain('general_settings.date_display.validation.invalid');
  });

  it('should not persist an empty format, reporting both the empty and the format rule', async () => {
    const wrapper = createWrapper();
    await input(wrapper, '');
    expect(get(model)).toBe('%d/%m/%Y');
    expect(wrapper.find('.error').text()).toContain('general_settings.date_display.validation.empty');
    expect(wrapper.find('.error-count').text()).toBe('2');
  });

  it('should reset to the default format and flush immediately', async () => {
    const wrapper = createWrapper();
    await wrapper.find('.reset').trigger('click');
    await nextTick();
    expect(get(model)).toBe('%d/%m/%Y %H:%M:%S %Z');
    expect(wrapper.find('.model').text()).toBe('%d/%m/%Y %H:%M:%S %Z');
    expect(flushMock).toHaveBeenCalledOnce();
  });

  it('should reflect an external change of the setting', async () => {
    const wrapper = createWrapper();
    set(model, '%Y');
    await nextTick();
    expect(wrapper.find('.model').text()).toBe('%Y');
  });

  it('should show a success message once the write lands', async () => {
    const wrapper = createWrapper();
    set(success, true);
    await nextTick();
    expect(wrapper.find('.success').text()).toContain('general_settings.validation.date_display_format.success');
  });

  it('should show a prefixed error message when the write fails', async () => {
    const wrapper = createWrapper();
    set(error, 'boom');
    await nextTick();
    expect(wrapper.find('.error').text()).toBe('settings.not_saved: general_settings.validation.date_display_format.error: boom');
  });

  it('should render the formatted example as the hint', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.hint').text()).toContain('general_settings.date_display_format_hint::');
  });
});
