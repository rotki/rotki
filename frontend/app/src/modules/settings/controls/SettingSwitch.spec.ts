import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { useSettingModelMock } = vi.hoisted(() => ({ useSettingModelMock: vi.fn() }));
vi.mock('@/modules/settings/use-setting-model', () => ({ useSettingModel: useSettingModelMock }));

const RuiSwitchStub = {
  props: ['modelValue', 'successMessages', 'errorMessages', 'label'],
  emits: ['update:model-value'],
  template: `<div>
    <span class="model">{{ modelValue }}</span>
    <span class="success">{{ successMessages }}</span>
    <span class="error">{{ errorMessages }}</span>
  </div>`,
};

const RuiCheckboxStub = {
  props: ['modelValue', 'label'],
  template: `<div class="checkbox"><span class="model">{{ modelValue }}</span></div>`,
};

describe('settingSwitch', () => {
  let model: Ref<boolean>;
  let error: Ref<string>;
  let success: Ref<boolean>;

  function createWrapper(props: Record<string, unknown> = {}): VueWrapper {
    return mount(SettingSwitch, {
      props: { setting: 'treatEth2AsEth', label: 'Treat', ...props },
      global: { stubs: { RuiCheckbox: RuiCheckboxStub, RuiSwitch: RuiSwitchStub } },
    });
  }

  beforeEach(() => {
    model = ref<boolean>(false);
    error = ref<string>('');
    success = ref<boolean>(false);
    useSettingModelMock.mockReturnValue({ error, model, pending: ref(false), success });
  });

  it('should bind the switch to the setting draft', () => {
    set(model, true);
    const wrapper = createWrapper();
    expect(wrapper.find('.model').text()).toBe('true');
  });

  it('should show a saved message after a successful write', async () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.success').text()).toBe('');
    set(success, true);
    await nextTick();
    expect(wrapper.find('.success').text()).not.toBe('');
  });

  it('should derive the success message from the persisted value when given a callback', async () => {
    const successMessage = (value: boolean): string => (value ? 'turned on' : 'turned off');
    set(model, true);
    const wrapper = createWrapper({ successMessage });
    set(success, true);
    await nextTick();
    expect(wrapper.find('.success').text()).toContain('turned on');
  });

  it('should surface the write error message', async () => {
    const wrapper = createWrapper();
    set(error, 'boom');
    await nextTick();
    expect(wrapper.find('.error').text()).toContain('boom');
  });

  it('should clear messages when the draft changes again', async () => {
    const wrapper = createWrapper();
    set(error, 'boom');
    await nextTick();
    set(model, true);
    await nextTick();
    expect(wrapper.find('.error').text()).toBe('');
  });

  it('should emit updated with the persisted value after a successful write', async () => {
    set(model, true);
    const wrapper = createWrapper();
    set(success, true);
    await nextTick();
    expect(wrapper.emitted('updated')).toStrictEqual([[true]]);
  });

  it('should coerce a nullish draft to false for the switch', () => {
    const nullableModel = ref<boolean | null | undefined>(null);
    useSettingModelMock.mockReturnValue({ error, model: nullableModel, pending: ref(false), success });
    const wrapper = createWrapper({ setting: 'includeFeesInCostBasis' });
    expect(wrapper.find('.model').text()).toBe('false');
  });

  it('should treat a nullish draft as off in a callback success message', async () => {
    const successMessage = (value: boolean): string => (value ? 'turned on' : 'turned off');
    const nullableModel = ref<boolean | null | undefined>(null);
    useSettingModelMock.mockReturnValue({ error, model: nullableModel, pending: ref(false), success });
    const wrapper = createWrapper({ setting: 'includeFeesInCostBasis', successMessage });
    set(success, true);
    await nextTick();
    expect(wrapper.find('.success').text()).toContain('turned off');
  });

  it('should display the negated value when inverted', () => {
    set(model, true);
    const wrapper = createWrapper({ inverted: true });
    expect(wrapper.find('.model').text()).toBe('false');
  });

  it('should write the negated value when inverted', async () => {
    set(model, true);
    const wrapper = createWrapper({ inverted: true });
    await wrapper.findComponent(RuiSwitchStub).vm.$emit('update:model-value', true);
    await nextTick();
    expect(get(model)).toBe(false);
  });

  it('should render a checkbox when control is checkbox', () => {
    const wrapper = createWrapper({ control: 'checkbox' });
    expect(wrapper.find('.checkbox').exists()).toBe(true);
  });
});
