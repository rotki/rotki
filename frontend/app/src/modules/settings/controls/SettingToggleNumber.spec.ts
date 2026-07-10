import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import SettingToggleNumber from '@/modules/settings/controls/SettingToggleNumber.vue';

const { flushMock, useSettingModelMock } = vi.hoisted(() => ({ flushMock: vi.fn(), useSettingModelMock: vi.fn() }));
vi.mock('@/modules/settings/use-setting-model', () => ({ useSettingModel: useSettingModelMock }));

const RuiSwitchStub = {
  props: ['modelValue', 'label'],
  emits: ['update:model-value'],
  template: `<div class="switch"><span class="switch-model">{{ modelValue }}</span></div>`,
};

const RuiTextFieldStub = {
  props: ['modelValue', 'successMessages', 'errorMessages', 'disabled'],
  emits: ['update:model-value'],
  template: `<div class="field">
    <span class="field-model">{{ modelValue }}</span>
    <span class="success">{{ successMessages }}</span>
    <span class="disabled">{{ disabled }}</span>
  </div>`,
};

describe('settingToggleNumber', () => {
  let model: Ref<number>;
  let error: Ref<string>;
  let success: Ref<boolean>;

  function createWrapper(props: Record<string, unknown> = {}): VueWrapper {
    return mount(SettingToggleNumber, {
      props: {
        enabledValue: 30,
        fieldLabel: 'Period',
        min: 30,
        setting: 'refreshPeriod',
        switchLabel: 'Enable',
        validation: { empty: 'required', invalid: 'invalid' },
        ...props,
      },
      global: { stubs: { RuiSwitch: RuiSwitchStub, RuiTextField: RuiTextFieldStub } },
    });
  }

  beforeEach(() => {
    flushMock.mockClear();
    model = ref<number>(60);
    error = ref<string>('');
    success = ref<boolean>(false);
    useSettingModelMock.mockReturnValue({ error, flush: flushMock, model, pending: ref(false), success });
  });

  it('should render the switch on and the field value when the stored value is positive', () => {
    const wrapper = createWrapper({ max: 3600 });
    expect(wrapper.find('.switch-model').text()).toBe('true');
    expect(wrapper.find('.field-model').text()).toBe('60');
    expect(wrapper.find('.disabled').text()).toBe('false');
  });

  it('should write the sentinel and flush when toggled off', async () => {
    const wrapper = createWrapper({ max: 3600, offValue: -1 });
    await wrapper.findComponent(RuiSwitchStub).vm.$emit('update:model-value', false);
    await nextTick();
    expect(get(model)).toBe(-1);
    expect(flushMock).toHaveBeenCalledOnce();
  });

  it('should write the enabled value and flush when toggled on', async () => {
    set(model, -1);
    const wrapper = createWrapper({ max: 3600 });
    await wrapper.findComponent(RuiSwitchStub).vm.$emit('update:model-value', true);
    await nextTick();
    expect(get(model)).toBe(30);
    expect(flushMock).toHaveBeenCalledOnce();
  });

  it('should persist a valid field value', async () => {
    const wrapper = createWrapper({ max: 3600 });
    await wrapper.findComponent(RuiTextFieldStub).vm.$emit('update:model-value', '120');
    await nextTick();
    expect(get(model)).toBe(120);
  });

  it('should map stored value through toField/fromField', async () => {
    set(model, 60);
    const wrapper = createWrapper({
      fromField: (days: string) => Number.parseInt(days) * 60,
      min: 1,
      toField: (seconds: number) => String(seconds / 60),
    });
    expect(wrapper.find('.field-model').text()).toBe('1');
    await wrapper.findComponent(RuiTextFieldStub).vm.$emit('update:model-value', '5');
    await nextTick();
    expect(get(model)).toBe(300);
  });

  it('should show a per-action success message from numberSuccess', async () => {
    const wrapper = createWrapper({ max: 3600, success: { onValue: (value: string) => `saved ${value}` } });
    await wrapper.findComponent(RuiTextFieldStub).vm.$emit('update:model-value', '90');
    await nextTick();
    set(success, true);
    await nextTick();
    expect(wrapper.find('.success').text()).toContain('saved 90');
  });

  it('should disable the field when off', () => {
    set(model, -1);
    const wrapper = createWrapper({ max: 3600 });
    expect(wrapper.find('.disabled').text()).toBe('true');
  });
});
