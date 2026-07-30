import type { ActiveFilter, FieldDef } from '@/modules/core/table/pill/core/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import RangeValueEditor from '@/modules/core/table/pill/RangeValueEditor.vue';

const ButtonGroupStub = defineComponent({
  name: 'RuiButtonGroup',
  props: { modelValue: { default: undefined, type: String } },
  emits: ['update:modelValue'],
  template: '<div data-testid="operators"><slot /></div>',
});

const field: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'matcher' },
  key: 'amount',
  label: 'Amount',
  multiple: false,
  operators: ['between', 'gt', 'lt'],
  valueType: 'range',
};

function createWrapper(filter: ActiveFilter): VueWrapper<InstanceType<typeof RangeValueEditor>> {
  return mount(RangeValueEditor, {
    global: { stubs: { RuiButtonGroup: ButtonGroupStub } },
    props: { field, filter },
  });
}

describe('rangeValueEditor', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should show both bounds for between', () => {
    const wrapper = createWrapper({ fieldKey: 'amount', op: 'between', values: [] });
    expect(wrapper.find('[data-testid=range-min]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=range-max]').exists()).toBe(true);
  });

  it('should show only the min for gt and only the max for lt', () => {
    const gt = createWrapper({ fieldKey: 'amount', op: 'gt', values: [] });
    expect(gt.find('[data-testid=range-min]').exists()).toBe(true);
    expect(gt.find('[data-testid=range-max]').exists()).toBe(false);

    const lt = createWrapper({ fieldKey: 'amount', op: 'lt', values: [] });
    expect(lt.find('[data-testid=range-min]').exists()).toBe(false);
    expect(lt.find('[data-testid=range-max]').exists()).toBe(true);
  });

  it('should emit the updated min bound after the debounce', async () => {
    const wrapper = createWrapper({ fieldKey: 'amount', op: 'between', range: { max: '9' }, values: [] });
    await wrapper.find('[data-testid=range-min] input').setValue('1');
    expect(wrapper.emitted('update')).toBeUndefined();
    await vi.advanceTimersByTimeAsync(400);
    expect(wrapper.emitted('update')?.[0]).toStrictEqual([
      { fieldKey: 'amount', op: 'between', range: { max: '9', min: '1' }, values: [] },
    ]);
  });

  it('should clear a bound when emptied', async () => {
    const wrapper = createWrapper({ fieldKey: 'amount', op: 'between', range: { max: '9', min: '1' }, values: [] });
    await wrapper.find('[data-testid=range-min] input').setValue('');
    await vi.advanceTimersByTimeAsync(400);
    expect(wrapper.emitted('update')?.[0]).toStrictEqual([
      { fieldKey: 'amount', op: 'between', range: { max: '9', min: undefined }, values: [] },
    ]);
  });

  it('should not emit and should flag both fields when max is below min', async () => {
    const wrapper = createWrapper({ fieldKey: 'amount', op: 'between', range: { min: '5' }, values: [] });
    await wrapper.find('[data-testid=range-max] input').setValue('1');
    await vi.advanceTimersByTimeAsync(400);
    expect(wrapper.emitted('update')).toBeUndefined();
    expect(wrapper.find('[data-testid=range-min]').text()).toContain('transactions.filter.range_max_below_min');
    expect(wrapper.find('[data-testid=range-max]').text()).toContain('transactions.filter.range_max_below_min');
  });

  it('should resume emitting once the range becomes valid again', async () => {
    const wrapper = createWrapper({ fieldKey: 'amount', op: 'between', range: { min: '5' }, values: [] });
    await wrapper.find('[data-testid=range-max] input').setValue('1');
    await vi.advanceTimersByTimeAsync(400);
    expect(wrapper.emitted('update')).toBeUndefined();
    await wrapper.find('[data-testid=range-max] input').setValue('9');
    await vi.advanceTimersByTimeAsync(400);
    expect(wrapper.emitted('update')?.[0]).toStrictEqual([
      { fieldKey: 'amount', op: 'between', range: { max: '9', min: '5' }, values: [] },
    ]);
  });

  it('should drop the hidden bound when the operator changes', () => {
    const wrapper = createWrapper({ fieldKey: 'amount', op: 'between', range: { max: '9', min: '1' }, values: [] });
    wrapper.findComponent(ButtonGroupStub).vm.$emit('update:modelValue', 'gt');
    expect(wrapper.emitted('update')?.[0]).toStrictEqual([
      { fieldKey: 'amount', op: 'gt', range: { min: '1' }, values: [] },
    ]);
  });

  // Closing commits rather than cancels, so a range typed and then dismissed by clicking away is
  // not lost to the pending debounce.
  it('should commit a pending range when the editor closes', async () => {
    const wrapper = createWrapper({ fieldKey: 'amount', op: 'between', values: [] });

    await wrapper.find('[data-testid=range-min] input').setValue('100');
    expect(wrapper.emitted('update')).toBeUndefined();

    wrapper.unmount();

    expect(wrapper.emitted('update')?.[0]).toEqual([
      { fieldKey: 'amount', op: 'between', range: { max: undefined, min: '100' }, values: [] },
    ]);
  });

  it('should keep what is typed when the operator changes before the debounce', async () => {
    const wrapper = createWrapper({ fieldKey: 'amount', op: 'between', values: [] });

    await wrapper.find('[data-testid=range-min] input').setValue('100');
    // Switching now, with the commit still pending, must carry the typed bound across.
    await wrapper.findComponent({ name: 'RuiButtonGroup' }).vm.$emit('update:modelValue', 'gt');

    const update = wrapper.emitted('update')?.at(-1)?.[0];
    expect(update).toEqual({ fieldKey: 'amount', op: 'gt', range: { min: '100' }, values: [] });
  });
});
