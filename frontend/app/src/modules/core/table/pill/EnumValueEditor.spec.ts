import type { ActiveFilter, FieldDef } from '@/modules/core/table/pill/core/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import EnumValueEditor from '@/modules/core/table/pill/EnumValueEditor.vue';
import ValueSelectList from '@/modules/core/table/pill/ValueSelectList.vue';

const ButtonGroupStub = defineComponent({
  name: 'RuiButtonGroup',
  props: { modelValue: { default: undefined, type: String } },
  emits: ['update:modelValue'],
  template: '<div data-testid="operators"><slot /></div>',
});

const enumField: FieldDef = {
  allowExclusion: true,
  binding: { kind: 'filter' },
  key: 'protocols',
  label: 'Protocol',
  multiple: true,
  operators: ['is', 'is_not'],
  suggest: (): string[] => ['aave', 'uniswap'],
  valueType: 'enum',
};

function createWrapper(field: FieldDef, filter: ActiveFilter): VueWrapper<InstanceType<typeof EnumValueEditor>> {
  return mount(EnumValueEditor, {
    global: { stubs: { RuiButtonGroup: ButtonGroupStub } },
    props: { field, filter },
  });
}

describe('enumValueEditor', () => {
  it('should derive checklist options from the field suggestions', () => {
    const wrapper = createWrapper(enumField, { fieldKey: 'protocols', op: 'is', values: [] });
    expect(wrapper.findComponent(ValueSelectList).props('options')).toStrictEqual([
      { caption: undefined, keywords: undefined, loading: undefined, label: 'aave', value: 'aave' },
      { caption: undefined, keywords: undefined, loading: undefined, label: 'uniswap', value: 'uniswap' },
    ]);
  });

  it('should map option labels through the field resolver when present', () => {
    const wrapper = createWrapper(
      { ...enumField, resolveLabel: (value: string): string => value.toUpperCase() },
      { fieldKey: 'protocols', op: 'is', values: [] },
    );
    expect(wrapper.findComponent(ValueSelectList).props('options')).toStrictEqual([
      { caption: undefined, keywords: undefined, loading: undefined, label: 'AAVE', value: 'aave' },
      { caption: undefined, keywords: undefined, loading: undefined, label: 'UNISWAP', value: 'uniswap' },
    ]);
  });

  it('should carry the field captions and keywords onto the options', () => {
    const wrapper = createWrapper(
      {
        ...enumField,
        resolveCaption: (value: string): string => `caption:${value}`,
        resolveKeywords: (value: string): string => `keywords:${value}`,
      },
      { fieldKey: 'protocols', op: 'is', values: [] },
    );
    expect(wrapper.findComponent(ValueSelectList).props('options')).toStrictEqual([
      { caption: 'caption:aave', keywords: 'keywords:aave', loading: undefined, label: 'aave', value: 'aave' },
      { caption: 'caption:uniswap', keywords: 'keywords:uniswap', loading: undefined, label: 'uniswap', value: 'uniswap' },
    ]);
  });

  it('should emit the updated values on selection', () => {
    const wrapper = createWrapper(enumField, { fieldKey: 'protocols', op: 'is', values: [] });
    wrapper.findComponent(ValueSelectList).vm.$emit('update:modelValue', ['aave', 'uniswap']);
    expect(wrapper.emitted('update')?.[0]).toStrictEqual([{ fieldKey: 'protocols', op: 'is', values: ['aave', 'uniswap'] }]);
  });

  it('should show the operator toggle only when more than one operator is allowed', () => {
    const wrapper = createWrapper(enumField, { fieldKey: 'protocols', op: 'is', values: [] });
    expect(wrapper.findComponent(ButtonGroupStub).exists()).toBe(true);

    const single = createWrapper(
      { ...enumField, operators: ['is'] },
      { fieldKey: 'protocols', op: 'is', values: [] },
    );
    expect(single.findComponent(ButtonGroupStub).exists()).toBe(false);
  });

  it('should emit the new operator on toggle', () => {
    const wrapper = createWrapper(enumField, { fieldKey: 'protocols', op: 'is', values: ['aave'] });
    wrapper.findComponent(ButtonGroupStub).vm.$emit('update:modelValue', 'is_not');
    expect(wrapper.emitted('update')?.[0]).toStrictEqual([{ fieldKey: 'protocols', op: 'is_not', values: ['aave'] }]);
  });
  it('should forward the list being dismissed as its own close', () => {
    const wrapper = createWrapper(enumField, { fieldKey: 'protocols', op: 'is', values: [] });

    wrapper.findComponent(ValueSelectList).vm.$emit('close');

    expect(wrapper.emitted('close')).toHaveLength(1);
  });
});
