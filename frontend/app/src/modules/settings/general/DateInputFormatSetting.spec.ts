import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import DateInputFormatSetting from '@/modules/settings/general/DateInputFormatSetting.vue';

const { useSettingModelMock } = vi.hoisted(() => ({ useSettingModelMock: vi.fn() }));
vi.mock('@/modules/settings/use-setting-model', () => ({ useSettingModel: useSettingModelMock }));

const SelectorStub = {
  props: ['modelValue', 'successMessages', 'errorMessages', 'label'],
  emits: ['update:model-value'],
  template: `<div>
    <span class="model">{{ modelValue }}</span>
    <span class="success">{{ successMessages }}</span>
    <span class="error">{{ errorMessages }}</span>
    <span class="error-count">{{ errorMessages.length }}</span>
  </div>`,
};

describe('dateInputFormatSetting', () => {
  let model: Ref<string>;
  let error: Ref<string>;
  let success: Ref<boolean>;

  function createWrapper(): VueWrapper {
    return mount(DateInputFormatSetting, {
      global: { stubs: { DateInputFormatSelector: SelectorStub } },
    });
  }

  async function input(wrapper: VueWrapper, value: string): Promise<void> {
    await wrapper.findComponent(SelectorStub).vm.$emit('update:model-value', value);
    await nextTick();
  }

  beforeEach(() => {
    model = ref<string>('%d/%m/%Y %H:%M:%S');
    error = ref<string>('');
    success = ref<boolean>(false);
    useSettingModelMock.mockReturnValue({ error, flush: vi.fn(), model, pending: ref(false), success });
  });

  it('should render the selector with the current value', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.model').text()).toBe('%d/%m/%Y %H:%M:%S');
  });

  it('should persist a format that contains valid directives', async () => {
    const wrapper = createWrapper();
    await input(wrapper, '%Y-%m-%d');
    expect(get(model)).toBe('%Y-%m-%d');
    expect(wrapper.find('.error-count').text()).toBe('0');
  });

  it('should not persist a format without valid directives', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 'nonsense');
    expect(get(model)).toBe('%d/%m/%Y %H:%M:%S');
    expect(wrapper.find('.error').text()).toContain('general_settings.date_display.validation.invalid');
  });

  it('should not persist an empty format, reporting both the empty and the format rule', async () => {
    const wrapper = createWrapper();
    await input(wrapper, '');
    expect(get(model)).toBe('%d/%m/%Y %H:%M:%S');
    expect(wrapper.find('.error').text()).toContain('general_settings.date_display.validation.empty');
    expect(wrapper.find('.error-count').text()).toBe('2');
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
    expect(wrapper.find('.success').text()).toContain('general_settings.validation.date_input_format.success');
  });

  it('should show the write error alone, replacing the validation messages', async () => {
    const wrapper = createWrapper();
    set(error, 'boom');
    await nextTick();
    expect(wrapper.find('.error').text()).toContain('settings.not_saved: general_settings.validation.date_input_format.error: boom');
    expect(wrapper.find('.error-count').text()).toBe('1');
  });
});
