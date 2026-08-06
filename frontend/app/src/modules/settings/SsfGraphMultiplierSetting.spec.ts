import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import SsfGraphMultiplierSetting from '@/modules/settings/SsfGraphMultiplierSetting.vue';

const { useSettingMock, useSettingModelMock } = vi.hoisted(() => ({
  useSettingMock: vi.fn(),
  useSettingModelMock: vi.fn(),
}));
vi.mock('@/modules/settings/use-setting-model', () => ({ useSettingModel: useSettingModelMock }));
vi.mock('@/modules/settings/use-setting', () => ({ useSetting: useSettingMock }));

const RuiTextFieldStub = {
  props: ['modelValue', 'successMessages', 'errorMessages', 'label'],
  emits: ['update:model-value'],
  template: `<div>
    <span class="model">{{ modelValue }}</span>
    <span class="success">{{ successMessages }}</span>
    <span class="error">{{ errorMessages }}</span>
    <span class="error-count">{{ Array.isArray(errorMessages) ? errorMessages.length : (errorMessages ? 1 : 0) }}</span>
  </div>`,
};

describe('ssfGraphMultiplierSetting', () => {
  let model: Ref<number>;
  let error: Ref<string>;
  let success: Ref<boolean>;

  function createWrapper(): VueWrapper {
    return mount(SsfGraphMultiplierSetting, {
      global: { stubs: { RuiCardHeader: true, RuiTextField: RuiTextFieldStub } },
    });
  }

  async function input(wrapper: VueWrapper, value: string): Promise<void> {
    await wrapper.findComponent(RuiTextFieldStub).vm.$emit('update:model-value', value);
    await nextTick();
  }

  beforeEach(() => {
    model = ref<number>(0);
    error = ref<string>('');
    success = ref<boolean>(false);
    useSettingMock.mockReturnValue(ref(3600));
    useSettingModelMock.mockReturnValue({ error, flush: vi.fn(), model, pending: ref(false), success });
  });

  it('should render the field with the current value', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.model').text()).toBe('0');
  });

  it('should persist a positive multiplier as a number', async () => {
    const wrapper = createWrapper();
    await input(wrapper, '10');
    expect(get(model)).toBe(10);
    expect(wrapper.find('.error-count').text()).toBe('0');
  });

  it('should not persist a negative multiplier', async () => {
    const wrapper = createWrapper();
    await input(wrapper, '-1');
    expect(get(model)).toBe(0);
    expect(wrapper.find('.error').text()).toContain('statistics_graph_settings.multiplier.validations.positive_number');
  });

  it('should persist an empty value as zero', async () => {
    set(model, 10);
    const wrapper = createWrapper();
    await input(wrapper, '');
    expect(get(model)).toBe(0);
    expect(wrapper.find('.error-count').text()).toBe('0');
  });

  it('should report the period as off while the multiplier is zero', () => {
    const wrapper = createWrapper();
    expect(wrapper.text()).toContain('statistics_graph_settings.multiplier.off');
  });

  it('should report the period as the multiplier times the save frequency', async () => {
    const wrapper = createWrapper();
    await input(wrapper, '10');
    expect(wrapper.text()).toContain('statistics_graph_settings.multiplier.on::36000');
  });

  it('should reflect an external change of the setting', async () => {
    const wrapper = createWrapper();
    set(model, 7);
    await nextTick();
    expect(wrapper.find('.model').text()).toBe('7');
  });

  it('should emit updated and show success once the write lands', async () => {
    const wrapper = createWrapper();
    set(success, true);
    await nextTick();
    expect(wrapper.emitted('updated')).toHaveLength(1);
    expect(wrapper.find('.success').text()).toContain('settings.saved');
  });

  it('should show the write error unprefixed by a setting-specific message', async () => {
    const wrapper = createWrapper();
    set(error, 'boom');
    await nextTick();
    expect(wrapper.find('.error').text()).toContain('settings.not_saved: boom');
  });
});
