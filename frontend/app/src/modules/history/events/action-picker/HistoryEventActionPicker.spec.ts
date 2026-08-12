import type { EventActionRow } from '@/modules/history/events/action-picker/use-event-action-picker';
import { mount } from '@vue/test-utils';
import { kebabCase } from 'es-toolkit';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
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

const RuiCategoryPickerStub = defineComponent((props: {
  categoryOf?: (item: EventActionRow) => string;
  items: EventActionRow[];
  label?: string;
  modelValue?: string;
  search?: string;
}, { emit, slots }) => (): VNode => {
  const query = (props.search ?? '').trim().toLowerCase();
  const visible = query
    ? props.items.filter(item => item.label.toLowerCase().includes(query))
    : props.items;

  const categoryOf = props.categoryOf;
  const categoryLabel = (item: EventActionRow): string => (categoryOf ? categoryOf(item) : '');
  const categories: string[] = [];
  for (const item of visible) {
    const category = categoryLabel(item);
    if (!categories.includes(category))
      categories.push(category);
  }

  const renderItem = (item: EventActionRow): VNode => h(
    'button',
    {
      'data-key': kebabCase(item.verbKey),
      'data-testid': 'option',
      'onClick': (): void => emit('update:modelValue', item.verbKey),
    },
    slots.item ? [slots.item({ active: false, item, selected: false })] : [item.label],
  );

  // NOT kebab-cased: the grouping test tells the display label ('Trade') apart from the raw group
  // id ('trade') by case alone, so normalising here would collapse both into one selector. The raw
  // value rides on `data-key`, and attribute values match case-sensitively, so the pair stays apart.
  const renderCategory = (category: string): VNode => h('div', { 'data-key': category, 'data-testid': 'category' }, [
    slots.category ? slots.category({ active: false, category, count: 0, label: category }) : null,
    ...visible.filter(item => categoryLabel(item) === category).map(renderItem),
  ]);

  return h('div', { 'data-testid': 'category-picker-stub' }, [
    h('div', { 'data-testid': 'picker-value' }, [props.modelValue ?? '']),
    h('div', { 'data-testid': 'picker-label' }, [props.label ?? '']),
    ...categories.map(renderCategory),
    visible.length === 0 && slots.empty
      ? h('div', { 'data-testid': 'empty-slot' }, [slots.empty()])
      : null,
    slots.footer ? h('div', { 'data-testid': 'footer-slot' }, [slots.footer({})]) : null,
  ]);
}, {
  emits: ['update:modelValue', 'update:search'],
  props: ['categoryOf', 'items', 'label', 'modelValue', 'search'],
});

describe('historyEventActionPicker', () => {
  beforeEach(() => {
    set(recentRef, []);
    record.mockClear();
  });

  function mountPicker(modelValue: { eventType: string; eventSubtype: string } | undefined = undefined): ReturnType<typeof mount<typeof HistoryEventActionPicker>> {
    return mount(HistoryEventActionPicker, {
      global: {
        stubs: { RuiCategoryPicker: RuiCategoryPickerStub, RuiIcon: true },
      },
      props: { 'modelValue': modelValue, 'onUpdate:modelValue': vi.fn() },
    });
  }

  it('should resolve modelValue to the matching verb key', async () => {
    findRowByTypeSubtype.mockReturnValue(row);
    const wrapper = mountPicker({ eventSubtype: 'spend', eventType: 'trade' });
    await flushPromises();

    expect(wrapper.find('[data-testid="picker-value"]').text()).toBe('swap out');
  });

  it('should pass undefined value when no selection', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    expect(wrapper.find('[data-testid="picker-value"]').text()).toBe('');
  });

  it('should emit update:modelValue with the row first combination when an option is selected', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    await wrapper.find('[data-testid=option][data-key="swap-out"]').trigger('click');
    await flushPromises();

    const updates = wrapper.emitted('update:modelValue') ?? [];
    expect(updates).toHaveLength(1);
    expect(updates[0][0]).toEqual({ eventSubtype: 'spend', eventType: 'trade' });
  });

  it('should ignore implicit clears from the underlying picker', async () => {
    // Guard against any stray update:modelValue with undefined. The picker is
    // required and has no clear affordance, so these implicit clears must be
    // discarded: the model value should only change in response to a row pick.
    findRowByTypeSubtype.mockReturnValue(row);
    const wrapper = mountPicker({ eventSubtype: 'spend', eventType: 'trade' });
    await flushPromises();

    const stub = wrapper.findComponent(RuiCategoryPickerStub);
    stub.vm.$emit('update:modelValue', undefined);
    await flushPromises();

    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('should render the row content in the item slot', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    expect(wrapper.find('[data-testid=event-action-picker-row][data-key=swap-out]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=event-action-picker-row][data-key=swap-out]').text()).toContain('Swap out');

    // The subtitle must reset the nowrap it inherits from RuiButton's label so
    // line-clamp-2 can actually wrap onto a second line.
    const subtitle = wrapper.find('[data-testid=event-action-picker-row][data-key=swap-out] .line-clamp-2');
    expect(subtitle.exists()).toBe(true);
    expect(subtitle.classes()).toContain('whitespace-normal');
  });

  it('should group items under their display label, not the raw group id', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    set(recentRef, ['swap out']);
    const wrapper = mountPicker();
    await flushPromises();

    // RuiCategoryPicker prints the category string in its detail header, so the
    // picker must feed it the human label ('Trade'), never the backend id.
    expect(wrapper.find('[data-testid=category][data-key="Trade"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=category][data-key="trade"]').exists()).toBe(false);
    // ...and the synthetic recent group must not leak its internal id.
    expect(wrapper.find('[data-testid=category][data-key="__recent__"]').exists()).toBe(false);
  });

  it('should render the keyboard hint in the footer slot', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    expect(wrapper.find('[data-testid="footer-slot"]').exists()).toBe(true);
  });

  it('should render a learn more link to the event types docs in the footer', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    const link = wrapper.find('[data-testid="event-action-picker-learn-more"]');
    expect(link.exists()).toBe(true);
    expect(link.attributes('href')).toContain('tax-accounting/event-types');
  });

  it('should not highlight any part of the label when the search is empty', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    const rowEl = wrapper.find('[data-testid=event-action-picker-row][data-key=swap-out]');
    expect(rowEl.find('.text-rui-primary').exists()).toBe(false);
    expect(rowEl.text()).toContain('Swap out');
  });

  it('should highlight the matched substring of the label while searching', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    wrapper.findComponent(RuiCategoryPickerStub).vm.$emit('update:search', 'swap');
    await flushPromises();

    const highlighted = wrapper.find('[data-testid=event-action-picker-row][data-key=swap-out] .text-rui-primary');
    expect(highlighted.exists()).toBe(true);
    expect(highlighted.text()).toBe('Swap');
  });

  it('should show the empty state with the query when nothing matches', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    wrapper.findComponent(RuiCategoryPickerStub).vm.$emit('update:search', 'zzz');
    await flushPromises();

    const empty = wrapper.find('[data-testid="event-action-picker-empty"]');
    expect(empty.exists()).toBe(true);
    expect(empty.text()).toContain('zzz');
  });

  it('should hide the empty state when the search matches a row', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    const wrapper = mountPicker();
    await flushPromises();

    wrapper.findComponent(RuiCategoryPickerStub).vm.$emit('update:search', 'swap');
    await flushPromises();

    expect(wrapper.find('[data-testid="event-action-picker-empty"]').exists()).toBe(false);
  });

  it('should pin recent verbs to a synthetic recent group', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    set(recentRef, ['swap out']);
    const wrapper = mountPicker();
    await flushPromises();

    expect(wrapper.find('[data-testid="event-action-picker-recent-header"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=option][data-key="recent-swap-out"]').exists()).toBe(true);
    // The canonical row in its own group is still present.
    expect(wrapper.find('[data-testid=option][data-key="swap-out"]').exists()).toBe(true);
  });

  it('should not render the recent group while searching', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    set(recentRef, ['swap out']);
    const wrapper = mountPicker();
    await flushPromises();

    wrapper.findComponent(RuiCategoryPickerStub).vm.$emit('update:search', 'swap');
    await flushPromises();

    expect(wrapper.find('[data-testid="event-action-picker-recent-header"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=option][data-key="recent-swap-out"]').exists()).toBe(false);
  });

  it('should record the canonical verb key when a recent row is picked', async () => {
    findRowByTypeSubtype.mockReturnValue(undefined);
    set(recentRef, ['swap out']);
    const wrapper = mountPicker();
    await flushPromises();

    await wrapper.find('[data-testid=option][data-key="recent-swap-out"]').trigger('click');
    await flushPromises();

    expect(record).toHaveBeenCalledWith('swap out');
    const updates = wrapper.emitted('update:modelValue') ?? [];
    expect(updates[0][0]).toEqual({ eventSubtype: 'spend', eventType: 'trade' });
  });
});
