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
  binding: { kind: 'matcher' },
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
      { label: 'aave', value: 'aave' },
      { label: 'uniswap', value: 'uniswap' },
    ]);
  });

  it('should map option labels through the field resolver when present', () => {
    const wrapper = createWrapper(
      { ...enumField, resolveLabel: (value: string): string => value.toUpperCase() },
      { fieldKey: 'protocols', op: 'is', values: [] },
    );
    expect(wrapper.findComponent(ValueSelectList).props('options')).toStrictEqual([
      { label: 'AAVE', value: 'aave' },
      { label: 'UNISWAP', value: 'uniswap' },
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
