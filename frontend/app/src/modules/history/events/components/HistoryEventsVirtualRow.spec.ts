import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { VirtualRow } from '@/modules/history/events/use-virtual-rows';
import { createMock } from '@test/utils/create-mock';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import HistoryEventsDetailItem from '@/modules/history/events/components/HistoryEventsDetailItem.vue';
import HistoryEventsGroupItem from '@/modules/history/events/components/HistoryEventsGroupItem.vue';
import HistoryEventsLoadMoreRow from '@/modules/history/events/components/HistoryEventsLoadMoreRow.vue';
import HistoryEventsMatchedMovementItem from '@/modules/history/events/components/HistoryEventsMatchedMovementItem.vue';
import HistoryEventsRowPlaceholder from '@/modules/history/events/components/HistoryEventsRowPlaceholder.vue';
import HistoryEventsSwapCollapseRow from '@/modules/history/events/components/HistoryEventsSwapCollapseRow.vue';
import HistoryEventsSwapItem from '@/modules/history/events/components/HistoryEventsSwapItem.vue';
import HistoryEventsVirtualRow from '@/modules/history/events/components/HistoryEventsVirtualRow.vue';
import { type HistoryEventsRowContext, provideHistoryEventsRowContext } from '@/modules/history/events/use-history-events-row-context';

function createEvent(identifier: number): HistoryEventEntry {
  return createMock<HistoryEventEntry>({ identifier });
}

const groupEvents = [createEvent(1), createEvent(2)];
const subgroupEvents = [createEvent(3), createEvent(4)];

function createContext(): HistoryEventsRowContext {
  return {
    actions: {
      addEvent: vi.fn(),
      addMissingRule: vi.fn(),
      deleteEvents: vi.fn(),
      deleteTransaction: vi.fn(),
      editEvent: vi.fn(),
      loadMore: vi.fn(),
      redecode: vi.fn(),
      redecodeWithOptions: vi.fn(),
      refresh: vi.fn(),
      toggleIgnore: vi.fn(),
      toggleMovementExpanded: vi.fn(),
      toggleShowIgnoredAssets: vi.fn(),
      toggleSwapExpanded: vi.fn(),
      unlinkEvent: vi.fn(),
      unlinkGroup: vi.fn(),
    },
    display: {
      duplicateHandlingStatus: computed(() => undefined),
      eventsLoading: ref(false),
      hideActions: computed<boolean>(() => false),
      variant: computed<'row' | 'card'>(() => 'row'),
    },
    highlight: {
      getHighlightType: vi.fn(),
      getSwapHighlightType: vi.fn(),
      isGroupHighlighted: vi.fn().mockReturnValue(false),
      isHighlighted: vi.fn().mockReturnValue(false),
      isSwapHighlighted: vi.fn().mockReturnValue(false),
    },
    lookups: {
      completeEventsForItem: vi.fn().mockReturnValue(groupEvents),
      completeSubgroupEvents: vi.fn().mockReturnValue(subgroupEvents),
      groupEvents: vi.fn().mockReturnValue(groupEvents),
      groupLocationLabel: vi.fn().mockReturnValue('kraken'),
      ignoredAssets: vi.fn().mockReturnValue(undefined),
    },
  };
}

let context: HistoryEventsRowContext;

/**
 * Mounted through a host so the row resolves its context the way the virtual table supplies it:
 * a provide from an ancestor, not a prop. Children are stubbed because what this component owns
 * is the choice of child and the arguments it hands over, not their rendering.
 */
function mountRow(row: VirtualRow): VueWrapper {
  return mount({
    components: { HistoryEventsVirtualRow },
    setup() {
      provideHistoryEventsRowContext(context);
      return { row };
    },
    template: '<HistoryEventsVirtualRow :row="row" />',
  }, {
    global: {
      provide: libraryDefaults,
      // `shallow` would stub the component under test too; only its children should be stubs.
      stubs: { HistoryEventsVirtualRow: false },
    },
    shallow: true,
  });
}

describe('modules/history/events/components/HistoryEventsVirtualRow', () => {
  beforeEach(() => {
    context = createContext();
  });

  it('should render a group header for a group-header row', () => {
    const group = createEvent(10);
    const wrapper = mountRow({ data: group, groupId: 'group-1', type: 'group-header' });

    const item = wrapper.findComponent(HistoryEventsGroupItem);
    expect(item.exists()).toBe(true);
    expect(item.props('group')).toBe(group);
    expect(item.props('groupEvents')).toBe(groupEvents);
    expect(context.lookups.groupEvents).toHaveBeenCalledWith('group-1');
    expect(wrapper.findComponent(HistoryEventsDetailItem).exists()).toBe(false);
  });

  it('should render a placeholder for an event-placeholder row', () => {
    const wrapper = mountRow({ groupId: 'group-1', index: 0, type: 'event-placeholder' });

    const placeholder = wrapper.findComponent(HistoryEventsRowPlaceholder);
    expect(placeholder.exists()).toBe(true);
    expect(placeholder.props('variant')).toBe('row');
  });

  it('should render a detail item for an event-row', () => {
    const event = createEvent(11);
    const wrapper = mountRow({ data: event, groupId: 'group-1', index: 2, type: 'event-row' });

    const item = wrapper.findComponent(HistoryEventsDetailItem);
    expect(item.exists()).toBe(true);
    expect(item.props('event')).toBe(event);
    expect(item.props('index')).toBe(2);
    expect(item.props('completeGroupEvents')).toBe(groupEvents);
    expect(item.props('groupLocationLabel')).toBe('kraken');
  });

  it('should render a swap item for a swap-row', () => {
    const wrapper = mountRow({
      events: subgroupEvents,
      groupId: 'group-1',
      index: 0,
      swapKey: 'group-1-3',
      type: 'swap-row',
    });

    const item = wrapper.findComponent(HistoryEventsSwapItem);
    expect(item.exists()).toBe(true);
    expect(item.props('events')).toBe(subgroupEvents);
    expect(item.props('completeGroupEvents')).toBe(subgroupEvents);
  });

  it('should render a collapse row for a swap-collapse row', () => {
    const wrapper = mountRow({
      bridge: true,
      eventCount: 3,
      groupId: 'group-1',
      swapKey: 'group-1-3',
      type: 'swap-collapse',
    });

    const item = wrapper.findComponent(HistoryEventsSwapCollapseRow);
    expect(item.exists()).toBe(true);
    expect(item.props('eventCount')).toBe(3);
    expect(item.props('labelType')).toBe('bridge');
  });

  it('should render a matched movement item for a matched-movement-row', () => {
    const wrapper = mountRow({
      events: subgroupEvents,
      groupId: 'group-1',
      index: 0,
      movementKey: 'group-1-3',
      type: 'matched-movement-row',
    });

    const item = wrapper.findComponent(HistoryEventsMatchedMovementItem);
    expect(item.exists()).toBe(true);
    expect(item.props('events')).toBe(subgroupEvents);
  });

  it('should render a movement collapse row for a matched-movement-collapse row', () => {
    const wrapper = mountRow({
      eventCount: 2,
      groupId: 'group-1',
      movementKey: 'group-1-3',
      type: 'matched-movement-collapse',
    });

    const item = wrapper.findComponent(HistoryEventsSwapCollapseRow);
    expect(item.exists()).toBe(true);
    expect(item.props('labelType')).toBe('movement');
    expect(item.props('eventCount')).toBe(2);
  });

  it('should render a load more row for a load-more row', () => {
    const wrapper = mountRow({ groupId: 'group-1', hiddenCount: 4, totalCount: 10, type: 'load-more' });

    const item = wrapper.findComponent(HistoryEventsLoadMoreRow);
    expect(item.exists()).toBe(true);
    expect(item.props('hiddenCount')).toBe(4);
  });

  it('should route a row callback to the context action with its group id', async () => {
    const event = createEvent(12);
    const wrapper = mountRow({ data: event, groupId: 'group-7', index: 0, type: 'event-row' });

    const payload = { type: 'delete', ids: [12] } as const;
    await wrapper.findComponent(HistoryEventsDetailItem).vm.$emit('delete-event', payload);
    expect(context.actions.deleteEvents).toHaveBeenCalledWith(payload);

    await wrapper.findComponent(HistoryEventsDetailItem).vm.$emit('refresh');
    expect(context.actions.refresh).toHaveBeenCalledTimes(1);
  });

  it('should expand a swap through the context rather than its own state', async () => {
    const wrapper = mountRow({
      bridge: false,
      eventCount: 3,
      groupId: 'group-1',
      swapKey: 'group-1-3',
      type: 'swap-collapse',
    });

    await wrapper.findComponent(HistoryEventsSwapCollapseRow).vm.$emit('collapse');
    expect(context.actions.toggleSwapExpanded).toHaveBeenCalledWith('group-1-3');
  });

  it('should load more events for the row group', async () => {
    const wrapper = mountRow({ groupId: 'group-9', hiddenCount: 4, totalCount: 10, type: 'load-more' });

    await wrapper.findComponent(HistoryEventsLoadMoreRow).vm.$emit('load-more');
    expect(context.actions.loadMore).toHaveBeenCalledWith('group-9');
  });

  it('should pass the card variant down when the context switches layout', () => {
    context.display.variant = computed<'row' | 'card'>(() => 'card');
    const wrapper = mountRow({ groupId: 'group-1', index: 0, type: 'event-placeholder' });

    expect(wrapper.findComponent(HistoryEventsRowPlaceholder).props('variant')).toBe('card');
  });
});
