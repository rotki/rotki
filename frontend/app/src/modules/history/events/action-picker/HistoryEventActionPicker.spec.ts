import type { EventActionRow } from '@/modules/history/events/action-picker/use-event-action-picker';
import { mount } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, type PropType, type VNode } from 'vue';
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

const recentRef = ref<string[]>([]);
const record = vi.fn<(verbKey: string) => void>();

vi.mock('@/modules/history/events/action-picker/use-recent-actions', () => ({
  useRecentActions: (): unknown => ({
    recent: recentRef,
    record,
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
  emits: ['update:modelValue', 'update:searchInput'],
  props: {
    groupBy: { default: undefined, type: Function as unknown as PropType<(item: EventActionRow) => string> },
    label: { default: '', type: String },
    modelValue: { default: undefined, type: String },
    options: { required: true, type: Array as () => EventActionRow[] },
    searchInput: { default: '', type: String },
  },
  setup(props, { emit, slots }) {
    return (): VNode => {
      const query = props.searchInput.trim().toLowerCase();
      const visible = query
        ? props.options.filter(item => item.label.toLowerCase().includes(query))
        : props.options;

      const groupBy = props.groupBy;
      const groups: string[] = [];
      for (const item of visible) {
        const group = groupBy ? groupBy(item) : '';
        if (!groups.includes(group))
          groups.push(group);
      }

      const renderItem = (item: EventActionRow): VNode => h(
        'button',
        {
          'data-testid': `option-${item.verbKey}`,
          'onClick': (): void => emit('update:modelValue', item.verbKey),
        },
        slots.item ? [slots.item({ item })] : [item.label],
      );

      const renderGroup = (group: string): VNode => h('div', { 'data-testid': `group-${group}` }, [
        slots['group-header'] ? slots['group-header']({ group }) : null,
        ...visible.filter(item => (groupBy ? groupBy(item) : '') === group).map(renderItem),
      ]);

      return h('div', { 'data-testid': 'autocomplete-stub' }, [
        h('div', { 'data-testid': 'autocomplete-value' }, [props.modelValue ?? '']),
        h('div', { 'data-testid': 'autocomplete-label' }, [props.label ?? '']),
        ...groups.map(renderGroup),
        visible.length === 0 && slots['no-data']
          ? h('div', { 'data-testid': 'no-data-slot' }, [slots['no-data']()])
          : null,
        slots.footer ? h('div', { 'data-testid': 'footer-slot' }, [slots.footer({})]) : null,
      ]);
    };
  },
});

describe('historyEventActionPicker', () => {
  beforeEach(() => {
    set(recentRef, []);
    record.mockClear();
  });

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

  it('should not highlight any part of the label when the search is empty', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    const rowEl = wrapper.find('[data-testid="event-action-picker-row-swap out"]');
    expect(rowEl.find('.text-rui-primary').exists()).toBe(false);
    expect(rowEl.text()).toContain('Swap out');
  });

  it('should highlight the matched substring of the label while searching', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    wrapper.findComponent(RuiAutoCompleteStub).vm.$emit('update:searchInput', 'swap');
    await flushPromises();

    const highlighted = wrapper.find('[data-testid="event-action-picker-row-swap out"] .text-rui-primary');
    expect(highlighted.exists()).toBe(true);
    expect(highlighted.text()).toBe('Swap');
  });

  it('should show the empty state with the query when nothing matches', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    wrapper.findComponent(RuiAutoCompleteStub).vm.$emit('update:searchInput', 'zzz');
    await flushPromises();

    const empty = wrapper.find('[data-testid="event-action-picker-empty"]');
    expect(empty.exists()).toBe(true);
    expect(empty.text()).toContain('zzz');
  });

  it('should hide the empty state when the search matches a row', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    wrapper.findComponent(RuiAutoCompleteStub).vm.$emit('update:searchInput', 'swap');
    await flushPromises();

    expect(wrapper.find('[data-testid="event-action-picker-empty"]').exists()).toBe(false);
  });

  it('should pin recent verbs to a synthetic recent group', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    set(recentRef, ['swap out']);
    const wrapper = mountPicker();
    await flushPromises();

    expect(wrapper.find('[data-testid="event-action-picker-recent-header"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="option-recent:swap out"]').exists()).toBe(true);
    // The canonical row in its own group is still present.
    expect(wrapper.find('[data-testid="option-swap out"]').exists()).toBe(true);
  });

  it('should not render the recent group while searching', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    set(recentRef, ['swap out']);
    const wrapper = mountPicker();
    await flushPromises();

    wrapper.findComponent(RuiAutoCompleteStub).vm.$emit('update:searchInput', 'swap');
    await flushPromises();

    expect(wrapper.find('[data-testid="event-action-picker-recent-header"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="option-recent:swap out"]').exists()).toBe(false);
  });

  it('should record the canonical verb key when a recent row is picked', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    set(recentRef, ['swap out']);
    const wrapper = mountPicker();
    await flushPromises();

    await wrapper.find('[data-testid="option-recent:swap out"]').trigger('click');
    await flushPromises();

    expect(record).toHaveBeenCalledWith('swap out');
    const updates = wrapper.emitted('update:modelValue') ?? [];
    expect(updates[0][0]).toEqual({ eventSubtype: 'spend', eventType: 'trade' });
  });
});
