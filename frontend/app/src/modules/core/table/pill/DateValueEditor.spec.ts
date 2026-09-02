import type { ActiveFilter, FieldDef } from '@/modules/core/table/pill/core/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { assert, describe, expect, it, type Mock, vi } from 'vitest';
import { defineComponent } from 'vue';
import DateValueEditor from '@/modules/core/table/pill/DateValueEditor.vue';

const ButtonGroupStub = defineComponent({
  name: 'RuiButtonGroup',
  props: { modelValue: { default: undefined, type: String } },
  emits: ['update:modelValue'],
  template: '<div data-testid="operators"><slot /></div>',
});

const DateTimePickerStub = defineComponent({
  name: 'RuiDateTimePicker',
  props: {
    autofocus: { default: false, type: Boolean },
    maxDate: { default: undefined, type: [Number, String] },
    menuOpen: { default: false, type: Boolean },
    minDate: { default: undefined, type: Number },
    modelValue: { default: undefined, type: Number },
    partialTime: { default: undefined, type: String },
  },
  emits: ['update:modelValue', 'update:menuOpen'],
  mounted(): void {
    if (this.autofocus)
      this.focus();
  },
  methods: {
    focus(): void {
      const input = this.$refs.input;
      if (input instanceof HTMLInputElement)
        input.focus();
    },
  },
  template: `<input ref="input" :value="modelValue" @input="$emit('update:modelValue', $event.target.value === '' ? undefined : Number($event.target.value))" >`,
});

const field: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'filter' },
  key: 'period',
  label: 'Period',
  multiple: false,
  operators: ['between', 'after', 'before'],
  valueType: 'date',
};

function createWrapper(
  filter: ActiveFilter,
  attachTo?: HTMLElement,
  fieldOverrides: Partial<FieldDef> = {},
): VueWrapper<InstanceType<typeof DateValueEditor>> {
  return mount(DateValueEditor, {
    attachTo,
    global: { stubs: { RuiButtonGroup: ButtonGroupStub, RuiDateTimePicker: DateTimePickerStub } },
    props: { field: { ...field, ...fieldOverrides }, filter },
  });
}

function boundProp(
  wrapper: VueWrapper<InstanceType<typeof DateValueEditor>>,
  testId: string,
  prop: 'autofocus' | 'maxDate' | 'minDate' | 'partialTime',
): unknown {
  const found = wrapper.findAllComponents(DateTimePickerStub)
    .find(component => component.attributes('data-testid') === testId);
  assert(found, `no picker with the test id ${testId}`);
  return found.props(prop);
}

function bounds(wrapper: VueWrapper<InstanceType<typeof DateValueEditor>>): {
  fromMax: unknown;
  toMin: unknown;
} {
  return {
    fromMax: boundProp(wrapper, 'date-from', 'maxDate'),
    toMin: boundProp(wrapper, 'date-to', 'minDate'),
  };
}

function hostWithEscapeListener(): { escaped: Mock; host: HTMLElement } {
  const host = document.createElement('div');
  document.body.appendChild(host);
  const escaped = vi.fn();
  host.addEventListener('keydown', escaped);
  return { escaped, host };
}

describe('dateValueEditor', () => {
  it('should show both ends for between', () => {
    const wrapper = createWrapper({ fieldKey: 'period', op: 'between', values: [] });
    expect(wrapper.find('[data-testid=date-from]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=date-to]').exists()).toBe(true);
  });

  it('should show only from for after and only to for before', () => {
    const after = createWrapper({ fieldKey: 'period', op: 'after', values: [] });
    expect(after.find('[data-testid=date-from]').exists()).toBe(true);
    expect(after.find('[data-testid=date-to]').exists()).toBe(false);

    const before = createWrapper({ fieldKey: 'period', op: 'before', values: [] });
    expect(before.find('[data-testid=date-from]').exists()).toBe(false);
    expect(before.find('[data-testid=date-to]').exists()).toBe(true);
  });

  it('should complete a date-only bound from its own end of the day', () => {
    const wrapper = createWrapper({ fieldKey: 'period', op: 'between', values: [] });

    expect(boundProp(wrapper, 'date-from', 'partialTime')).toBe('start');
    expect(boundProp(wrapper, 'date-to', 'partialTime')).toBe('end');
  });

  it('should let both bounds sit on the same second by default', () => {
    const filter: ActiveFilter = { date: { from: '1704067200', to: '1704153600' }, fieldKey: 'period', op: 'between', values: [] };

    expect(bounds(createWrapper(filter))).toStrictEqual({ fromMax: 1704153600, toMin: 1704067200 });
  });

  it('should keep a second between the bounds when the field forbids an equal pair', () => {
    const filter: ActiveFilter = { date: { from: '1704067200', to: '1704153600' }, fieldKey: 'period', op: 'between', values: [] };

    expect(bounds(createWrapper(filter, undefined, { allowEqualBounds: false })))
      .toStrictEqual({ fromMax: 1704153599, toMin: 1704067201 });
  });

  it('should cap the from bound at now while the to bound is empty', () => {
    const filter: ActiveFilter = { fieldKey: 'period', op: 'between', values: [] };

    expect(bounds(createWrapper(filter))).toStrictEqual({ fromMax: 'now', toMin: undefined });
  });

  it('should emit the from bound as the unix-second string the picker gives', async () => {
    const wrapper = createWrapper({ fieldKey: 'period', op: 'between', values: [] });
    await wrapper.find('[data-testid=date-from]').setValue('1704067200');
    expect(wrapper.emitted('update')?.[0]).toStrictEqual([
      { date: { from: '1704067200' }, fieldKey: 'period', op: 'between', values: [] },
    ]);
  });

  it('should clear the from bound when the picker emits empty', async () => {
    const wrapper = createWrapper({ date: { from: '1704067200' }, fieldKey: 'period', op: 'between', values: [] });
    await wrapper.find('[data-testid=date-from]').setValue('');
    expect(wrapper.emitted('update')?.[0]).toStrictEqual([
      { date: { from: undefined }, fieldKey: 'period', op: 'between', values: [] },
    ]);
  });

  it('should emit the new operator on toggle', () => {
    const wrapper = createWrapper({ fieldKey: 'period', op: 'between', values: [] });
    wrapper.findComponent(ButtonGroupStub).vm.$emit('update:modelValue', 'after');
    expect(wrapper.emitted('update')?.[0]).toStrictEqual([{ fieldKey: 'period', op: 'after', values: [] }]);
  });

  it('should focus the from bound on mount, through the picker\'s own autofocus prop', async () => {
    const wrapper = createWrapper({ fieldKey: 'period', op: 'between', values: [] }, document.body);
    await nextTick();

    expect(boundProp(wrapper, 'date-from', 'autofocus')).toBe(true);
    expect(document.activeElement).toBe(wrapper.get('[data-testid=date-from]').element);
    wrapper.unmount();
  });

  it('should focus the to bound when there is no from bound', async () => {
    const wrapper = createWrapper({ fieldKey: 'period', op: 'before', values: [] }, document.body);
    await nextTick();

    expect(boundProp(wrapper, 'date-to', 'autofocus')).toBe(true);
    expect(document.activeElement).toBe(wrapper.get('[data-testid=date-to]').element);
    wrapper.unmount();
  });

  it('should keep escape inside the editor while the calendar is up', async () => {
    const { escaped, host } = hostWithEscapeListener();
    const wrapper = createWrapper({ fieldKey: 'period', op: 'between', values: [] }, host);

    wrapper.findComponent(DateTimePickerStub).vm.$emit('update:menuOpen', true);
    await nextTick();
    await wrapper.find('[data-testid=date-from]').trigger('keydown.esc');

    expect(wrapper.emitted('close')).toBeUndefined();
    expect(escaped).not.toHaveBeenCalled();

    wrapper.unmount();
    host.remove();
  });

  it('should let escape out once the calendar is shut', async () => {
    const { escaped, host } = hostWithEscapeListener();
    const wrapper = createWrapper({ fieldKey: 'period', op: 'between', values: [] }, host);

    const picker = wrapper.findComponent(DateTimePickerStub).vm;
    picker.$emit('update:menuOpen', true);
    await nextTick();
    picker.$emit('update:menuOpen', false);
    await nextTick();
    await wrapper.find('[data-testid=date-from]').trigger('keydown.esc');

    expect(wrapper.emitted('close')).toHaveLength(1);
    expect(escaped).toHaveBeenCalledTimes(1);

    wrapper.unmount();
    host.remove();
  });

  it('should close on escape from either bound', async () => {
    const wrapper = createWrapper({ fieldKey: 'period', op: 'between', values: [] });

    await wrapper.find('[data-testid=date-from]').trigger('keydown.esc');
    await wrapper.find('[data-testid=date-to]').trigger('keydown.esc');

    expect(wrapper.emitted('close')).toHaveLength(2);
  });
});
