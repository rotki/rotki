import type { ActiveFilter, FieldDef } from '@/modules/core/table/pill/core/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, type Mock, vi } from 'vitest';
import { defineComponent } from 'vue';
import DateValueEditor from '@/modules/core/table/pill/DateValueEditor.vue';

const ButtonGroupStub = defineComponent({
  name: 'RuiButtonGroup',
  props: { modelValue: { default: undefined, type: String } },
  emits: ['update:modelValue'],
  template: '<div data-testid="operators"><slot /></div>',
});

// Emits an epoch number like the real picker (type="epoch"); an empty input emits undefined.
// It also honours `autofocus` on mount, as the real picker does, so the focus tests exercise the
// prop the editor actually sets rather than restating the template.
const DateTimePickerStub = defineComponent({
  name: 'RuiDateTimePicker',
  props: {
    autofocus: { default: false, type: Boolean },
    menuOpen: { default: false, type: Boolean },
    modelValue: { default: undefined, type: Number },
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
  binding: { kind: 'matcher' },
  key: 'period',
  label: 'Period',
  multiple: false,
  operators: ['between', 'after', 'before'],
  valueType: 'date',
};

function createWrapper(
  filter: ActiveFilter,
  attachTo?: HTMLElement,
): VueWrapper<InstanceType<typeof DateValueEditor>> {
  return mount(DateValueEditor, {
    attachTo,
    global: { stubs: { RuiButtonGroup: ButtonGroupStub, RuiDateTimePicker: DateTimePickerStub } },
    props: { field, filter },
  });
}

// Mounts into a host that records what escapes the editor: the editor stops the key on its own
// root while a calendar is up, and nothing above that root may see it.
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

  // Opening a date pill used to leave the caret nowhere, since the menu is told not to focus its
  // own content. Driven through the picker's `autofocus` prop rather than a ref: the picker moves
  // the caret to the first segment from its own focus handler, and doing it from outside lands at
  // the wrong point in its lifecycle, leaving the caret at the end of the value.
  it('should focus the from bound on mount', async () => {
    const wrapper = createWrapper({ fieldKey: 'period', op: 'between', values: [] }, document.body);
    await nextTick();

    expect(document.activeElement).toBe(wrapper.get('[data-testid=date-from]').element);
    wrapper.unmount();
  });

  // `before` renders no From bound, so the first field is the To one.
  it('should focus the to bound when there is no from bound', async () => {
    const wrapper = createWrapper({ fieldKey: 'period', op: 'before', values: [] }, document.body);
    await nextTick();

    expect(document.activeElement).toBe(wrapper.get('[data-testid=date-to]').element);
    wrapper.unmount();
  });

  // The editor had no escape handler and leaned on the menu being dismissed, but the picker's
  // calendar binds escape itself to close only the calendar, so the key never reached the editor.
  // The picker binds escape inside its calendar to close it and hand focus back to the field, so
  // emitting unconditionally collapsed both layers on one press. Innermost first.
  //
  // Both halves are asserted through a listener on the host: the editor renders inside `RuiMenu`,
  // whose popover closes on escape whatever the editor emits (`onLeave` ignores `persistent`), so
  // the key not leaving the editor is the part that actually keeps the pill open. The stub stands
  // in for the picker here, which means these cover the editor's contract only — the real
  // two-layer press is an e2e assertion.
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
