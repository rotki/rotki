import type { EventActionRow } from '@/modules/history/events/action-picker/use-event-action-picker';
import { mount } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { describe, expect, it, vi } from 'vitest';
import { defineComponent, type VNode } from 'vue';
import HistoryEventActionPicker from '@/modules/history/events/action-picker/HistoryEventActionPicker.vue';

function buildRow(): EventActionRow {
  return {
    combinations: [{ eventSubtype: 'spend', eventType: 'trade' }],
    direction: 'out',
    groupId: 'trade',
    icon: 'lu-coins',
    label: 'Swap out',
    verbKey: 'swap out',
  };
}

const row = buildRow();
const findRowByTypeSubtype = vi.fn<(t: string, s: string) => EventActionRow | undefined>();
const rowsRef = computed<readonly EventActionRow[]>(() => [row]);

vi.mock('@/modules/history/events/action-picker/use-event-action-picker', () => ({
  useEventActionPicker: (): unknown => ({
    findRowByTypeSubtype: (t: string, s: string): EventActionRow | undefined => findRowByTypeSubtype(t, s),
    rows: rowsRef,
  }),
}));

vi.mock('@/modules/history/events/mapping/use-history-event-mappings', () => ({
  useHistoryEventMappings: (): unknown => ({
    eventCategoryGroupsData: computed(() => ({
      trade: { icon: 'lu-arrow-left-right', label: 'Trade', order: 10 },
    })),
    getHistoryEventSubTypeName: (s: string): string => s,
    getHistoryEventTypeName: (s: string): string => s,
  }),
}));

const RuiAutoCompleteStub = defineComponent({
  emits: ['update:modelValue'],
  props: {
    label: { default: '', type: String },
    modelValue: { default: undefined, type: String },
    options: { required: true, type: Array as () => EventActionRow[] },
  },
  setup(props, { emit, slots }) {
    return (): VNode => h('div', { 'data-testid': 'autocomplete-stub' }, [
      h('div', { 'data-testid': 'autocomplete-value' }, [props.modelValue ?? '']),
      h('div', { 'data-testid': 'autocomplete-label' }, [props.label ?? '']),
      ...props.options.map(item => h(
        'button',
        {
          'data-testid': `option-${item.verbKey}`,
          'onClick': (): void => emit('update:modelValue', item.verbKey),
        },
        slots.item ? [slots.item({ item })] : [item.label],
      )),
      slots.footer ? h('div', { 'data-testid': 'footer-slot' }, [slots.footer({})]) : null,
    ]);
  },
});

describe('historyEventActionPicker', () => {
  function mountPicker(modelValue: { eventType: string; eventSubtype: string } | undefined = undefined): ReturnType<typeof mount<typeof HistoryEventActionPicker>> {
    return mount(HistoryEventActionPicker, {
      global: {
        stubs: { RuiAutoComplete: RuiAutoCompleteStub, RuiIcon: true },
      },
      props: { 'modelValue': modelValue, 'onUpdate:modelValue': vi.fn() },
    });
  }

  it('should resolve modelValue to the matching verb key', async () => {
    findRowByTypeSubtype.mockReturnValue(row);
    const wrapper = mountPicker({ eventSubtype: 'spend', eventType: 'trade' });
    await flushPromises();

    expect(wrapper.find('[data-testid="autocomplete-value"]').text()).toBe('swap out');
  });

  it('should pass undefined value when no selection', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    expect(wrapper.find('[data-testid="autocomplete-value"]').text()).toBe('');
  });

  it('should emit update:modelValue with the row first combination when an option is selected', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    await wrapper.find('[data-testid="option-swap out"]').trigger('click');
    await flushPromises();

    const updates = wrapper.emitted('update:modelValue') ?? [];
    expect(updates).toHaveLength(1);
    expect(updates[0][0]).toEqual({ eventSubtype: 'spend', eventType: 'trade' });
  });

  it('should ignore implicit clears from the underlying autocomplete', async () => {
    // RuiAutoComplete emits update:modelValue with undefined on Backspace-from-empty
    // and on internal options resync. The picker is required and has no clear
    // affordance, so these implicit clears must be discarded — the model value
    // should only change in response to a row pick.
    findRowByTypeSubtype.mockReturnValue(row);
    const wrapper = mountPicker({ eventSubtype: 'spend', eventType: 'trade' });
    await flushPromises();

    const stub = wrapper.findComponent(RuiAutoCompleteStub);
    stub.vm.$emit('update:modelValue', undefined);
    await flushPromises();

    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should render the row content in the item slot', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    expect(wrapper.find('[data-testid="event-action-picker-row-swap out"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="event-action-picker-row-swap out"]').text()).toContain('Swap out');
  });

  it('should render the keyboard hint in the footer slot', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    expect(wrapper.find('[data-testid="footer-slot"]').exists()).toBe(true);
  });
});
