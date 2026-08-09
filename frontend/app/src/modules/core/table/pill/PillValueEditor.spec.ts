import type { ActiveFilter, FieldDef, FilterValueType } from '@/modules/core/table/pill/core/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AssetValueEditor from '@/modules/core/table/pill/AssetValueEditor.vue';
import DateValueEditor from '@/modules/core/table/pill/DateValueEditor.vue';
import EnumValueEditor from '@/modules/core/table/pill/EnumValueEditor.vue';
import PillValueEditor from '@/modules/core/table/pill/PillValueEditor.vue';
import RangeValueEditor from '@/modules/core/table/pill/RangeValueEditor.vue';
import TextValueEditor from '@/modules/core/table/pill/TextValueEditor.vue';

function field(valueType: FilterValueType, overrides: Partial<FieldDef> = {}): FieldDef {
  return {
    allowExclusion: false,
    binding: { kind: 'filter' },
    key: 'k',
    label: 'K',
    multiple: false,
    operators: ['is'],
    valueType,
    ...overrides,
  };
}

function createWrapper(fieldDef: FieldDef, filter: ActiveFilter): VueWrapper<InstanceType<typeof PillValueEditor>> {
  return mount(PillValueEditor, {
    // AssetValueEditor pulls in the Pinia-backed asset search; stub it since this spec only
    // checks the dispatch, not the asset editor internals. The text editor reads the scramble
    // setting, so a pinia is still needed.
    global: {
      plugins: [createCustomPinia()],
      stubs: { AssetValueEditor: true, RuiAutoComplete: true, RuiButtonGroup: true, RuiTextField: true },
    },
    props: { field: fieldDef, filter },
  });
}

describe('pillValueEditor', () => {
  it('should render the enum editor for enum fields', () => {
    const wrapper = createWrapper(field('enum'), { fieldKey: 'k', op: 'is', values: [] });
    expect(wrapper.findComponent(EnumValueEditor).exists()).toBe(true);
  });

  it('should render the asset editor for asset fields', () => {
    const wrapper = createWrapper(field('asset'), { fieldKey: 'k', op: 'is', values: [] });
    expect(wrapper.findComponent(AssetValueEditor).exists()).toBe(true);
    expect(wrapper.findComponent(EnumValueEditor).exists()).toBe(false);
  });

  it('should render the text editor for free-text fields', () => {
    const wrapper = createWrapper(field('enum', { freeText: true }), { fieldKey: 'k', op: 'is', values: [] });
    expect(wrapper.findComponent(TextValueEditor).exists()).toBe(true);
    expect(wrapper.findComponent(EnumValueEditor).exists()).toBe(false);
  });

  it('should render the range editor for range fields', () => {
    const wrapper = createWrapper(field('range'), { fieldKey: 'k', op: 'between', values: [] });
    expect(wrapper.findComponent(RangeValueEditor).exists()).toBe(true);
  });

  it('should render the date editor for date fields', () => {
    const wrapper = createWrapper(field('date'), { fieldKey: 'k', op: 'between', values: [] });
    expect(wrapper.findComponent(DateValueEditor).exists()).toBe(true);
  });

  it('should render no editor for boolean fields', () => {
    const wrapper = createWrapper(field('boolean'), { fieldKey: 'k', op: 'is', values: [] });
    expect(wrapper.findComponent(EnumValueEditor).exists()).toBe(false);
    expect(wrapper.findComponent(RangeValueEditor).exists()).toBe(false);
    expect(wrapper.findComponent(DateValueEditor).exists()).toBe(false);
  });

  it('should propagate a child editor update', () => {
    const wrapper = createWrapper(field('range'), { fieldKey: 'k', op: 'between', values: [] });
    const updated: ActiveFilter = { fieldKey: 'k', op: 'gt', range: { min: '5' }, values: [] };
    wrapper.findComponent(RangeValueEditor).vm.$emit('update', updated);
    expect(wrapper.emitted('update')?.[0]).toStrictEqual([updated]);
  });
});
