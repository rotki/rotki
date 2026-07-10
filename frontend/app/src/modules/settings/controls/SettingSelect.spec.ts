import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import SettingSelect from '@/modules/settings/controls/SettingSelect.vue';

const { useSettingModelMock } = vi.hoisted(() => ({ useSettingModelMock: vi.fn() }));
vi.mock('@/modules/settings/use-setting-model', () => ({ useSettingModel: useSettingModelMock }));

const RuiMenuSelectStub = {
  props: ['modelValue', 'options', 'keyAttr', 'textAttr', 'successMessages', 'errorMessages'],
  emits: ['update:model-value'],
  template: `<div class="select">
    <span class="model">{{ modelValue }}</span>
    <span class="success">{{ successMessages }}</span>
    <slot name="item" :item="options[0]" />
  </div>`,
};

const RuiRadioGroupStub = {
  props: ['modelValue', 'successMessages', 'errorMessages'],
  emits: ['update:model-value'],
  template: `<div class="radio-group"><span class="model">{{ modelValue }}</span><slot /></div>`,
};

const RuiRadioStub = {
  props: ['value'],
  template: `<label class="radio" :data-value="value"><slot /></label>`,
};

describe('settingSelect', () => {
  let model: Ref<string>;
  let error: Ref<string>;
  let success: Ref<boolean>;

  function createWrapper(props: Record<string, unknown> = {}, slots: Record<string, string> = {}): VueWrapper {
    return mount(SettingSelect, {
      props: { setting: 'currencyLocation', options: ['before', 'after'], ...props },
      slots,
      global: {
        stubs: { RuiMenuSelect: RuiMenuSelectStub, RuiRadio: RuiRadioStub, RuiRadioGroup: RuiRadioGroupStub },
      },
    });
  }

  beforeEach(() => {
    model = ref<string>('after');
    error = ref<string>('');
    success = ref<boolean>(false);
    useSettingModelMock.mockReturnValue({ error, model, pending: ref(false), success });
  });

  it('should render a select with the current value by default', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.select .model').text()).toBe('after');
  });

  it('should persist the selected value', async () => {
    const wrapper = createWrapper();
    await wrapper.findComponent(RuiMenuSelectStub).vm.$emit('update:model-value', 'before');
    await nextTick();
    expect(get(model)).toBe('before');
  });

  it('should render a radio group and persist a radio selection', async () => {
    const wrapper = createWrapper({ control: 'radio' });
    expect(wrapper.find('.radio-group').exists()).toBe(true);
    expect(wrapper.findAll('.radio')).toHaveLength(2);
    await wrapper.findComponent(RuiRadioGroupStub).vm.$emit('update:model-value', 'before');
    await nextTick();
    expect(get(model)).toBe('before');
  });

  it('should show a callback success message after a successful write', async () => {
    const wrapper = createWrapper({ successMessage: (value: string) => `saved ${value}` });
    set(success, true);
    await nextTick();
    expect(wrapper.find('.select .success').text()).toContain('saved after');
  });

  it('should project object options via keyAttr and forward the item slot', () => {
    const wrapper = createWrapper(
      { keyAttr: 'id', options: [{ id: 'fifo', name: 'FIFO' }], textAttr: 'name' },
      { item: `<template #item="{ item }"><span class="custom">{{ item.name }}</span></template>` },
    );
    expect(wrapper.find('.custom').text()).toBe('FIFO');
  });
});
