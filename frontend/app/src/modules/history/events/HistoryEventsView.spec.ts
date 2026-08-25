import type { Collection } from '@/modules/core/common/collection';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import HistoryEventsView from '@/modules/history/events/HistoryEventsView.vue';

/**
 * The seam: what the page hands each of its four children, and where their events go. Every
 * decision behind those values belongs to a composable with its own spec - the filters, the
 * actions, the selection, and `use-history-events-view-actions` for the page's own handlers.
 */

const groups = ref<Collection<HistoryEventRow>>(
  createMock<Collection<HistoryEventRow>>({ data: [], found: 0, limit: 10, total: 0 }),
);
const processing = ref<boolean>(false);
const refreshing = ref<boolean>(false);
const overlayAvailable = ref<boolean>(false);
const duplicateHandlingStatus = ref<string | undefined>();
const groupIdentifiers = ref<string[] | undefined>();
const ignoreStatus = ref<{ ignoredCount: number; notIgnoredCount: number } | undefined>();
const includes = ref({ evmEvents: true });

const clearFilters = vi.fn();
const onActionChanged = vi.fn();
const onLocationLabelsChanged = vi.fn();
const setPage = vi.fn();
const handleSelectionAction = vi.fn();
const handleAccountingRuleRefresh = vi.fn();
const fetchDataAndLocations = vi.fn().mockResolvedValue(undefined);
const redecodeBy = vi.fn();
const redecodeBlocks = vi.fn();
const refreshAll = vi.fn().mockResolvedValue(undefined);
const dialogHandlers = { onHistoryEventSaved: vi.fn() };

const handleRedecode = vi.fn();
const handleUpdateEventIds = vi.fn();
const handleMovementChanged = vi.fn();
const handleBridgeChanged = vi.fn();

vi.mock('@/modules/history/events/use-history-events-view-actions', () => ({
  useHistoryEventsViewActions: (): unknown => ({
    groupedEventsByTxRef: ref({}),
    handleBridgeChanged,
    handleMovementChanged,
    handleRedecode,
    handleUpdateEventIds,
    originalGroups: ref([]),
  }),
}));

vi.mock('@/modules/history/events/composables', () => ({
  getDefaultToggles: (): unknown => ({ matchExactEvents: false, showIgnoredAssets: false, stateMarkers: [] }),
  useHistoryEventFields: (): unknown => computed(() => []),
  useHistoryEventNavigationConsumer: vi.fn(),
  useHistoryEventsActions: (): unknown => ({
    dialogHandlers,
    fetch: { dataAndLocations: fetchDataAndLocations, dataAndRedecode: vi.fn() },
    redecode: { blocks: redecodeBlocks, by: redecodeBy },
    refresh: { all: refreshAll },
  }),
  useHistoryEventsDeletion: (): unknown => ({}),
  useHistoryEventsDialogRouting: vi.fn(),
  useHistoryEventsFilters: (): unknown => ({
    action: ref(),
    clearFilters,
    duplicateHandlingStatus,
    filters: ref({}),
    groupIdentifiers,
    groupLoading: ref(false),
    groups,
    hasActiveFilters: ref(false),
    highlightedGroupIdentifier: ref(),
    highlightedIdentifiers: ref(),
    highlightTypes: ref(),
    identifiers: ref(),
    includes,
    locationLabels: ref([]),
    onActionChanged,
    onLocationLabelsChanged,
    pagination: ref({ limit: 10, page: 1 }),
    refetch: vi.fn(),
    requestPayload: computed(() => ({ limit: 10, offset: 0 })),
    setPage,
    sort: ref([]),
  }),
  useHistoryEventsOverlay: (): unknown => ({ available: overlayAvailable }),
  useHistoryEventsSelectionActions: (): unknown => ({
    handleAccountingRuleRefresh,
    handleSelectionAction,
    ignoreStatus,
    modelAccountingRuleToEdit: ref(),
    selectedEventIds: ref([1, 2]),
  }),
  useHistoryEventsSelectionMode: (): unknown => ({
    setAvailableIds: vi.fn(),
    setTotalMatchingCount: vi.fn(),
    state: ref({ isActive: false }),
  }),
  useHistoryEventsStatus: (): unknown => ({
    anyEventsDecoding: ref(false),
    processing,
    refreshing,
    sectionLoading: ref(false),
    shouldFetchEventsRegularly: ref(false),
  }),
  useHistoryEventsTableHeight: (): unknown => computed(() => 0),
  useUnmatchedAssetMovements: (): unknown => ({
    autoMatchLoading: ref(false),
    autoMatchMovement: vi.fn(),
    refreshUnmatchedAssetMovements: vi.fn(),
  }),
  useUnmatchedBridgeTransactions: (): unknown => ({
    autoMatchLoading: ref(false),
    refreshUnmatchedBridgeTransactions: vi.fn(),
  }),
}));

function stub(name: string, emits: string[] = [], props: string[] = []): ReturnType<typeof defineComponent> {
  return defineComponent({
    emits,
    name,
    props: Object.fromEntries(props.map(prop => [prop, { default: undefined, required: false, type: null }])),
    setup: (_props, { slots }) => (): unknown => h('div', { 'data-testid': name }, [
      slots.buttons?.(),
      slots.header?.(),
      slots.default?.(),
    ]),
  });
}

const ViewButtonsStub = stub('HistoryEventsViewButtons', ['refresh', 'show:dialog'], ['includeEvmEvents', 'loading', 'processing']);
const TableActionsStub = stub('HistoryEventsTableActions', ['redecode', 'selection:action', 'update:action', 'update:locationLabels'], ['fields', 'hideRedecodeButtons', 'ignoreStatus', 'processing', 'selection']);
const FiltersChipsStub = stub('HistoryEventsFiltersChips', ['refresh'], ['duplicateHandlingStatus', 'groupIdentifiers']);
const VirtualTableStub = stub('HistoryEventsVirtualTable', ['clear-filters', 'refresh', 'refresh:block-event', 'set-page', 'show:dialog', 'update-event-ids'], ['duplicateHandlingStatus', 'hasActiveFilters', 'highlight', 'processing', 'source']);
const DialogContainerStub = stub('HistoryEventsDialogContainer', ['accounting-rule-refresh', 'bridge-matched', 'movement-matched'], ['eventHandlers', 'loading', 'refreshing', 'sectionLoading', 'selectedEventIds']);
const TablePageLayoutStub = stub('TablePageLayout', [], ['child', 'hideHeader', 'title']);
const OverlayToggleStub = stub('AccountingOverlayToggle');

describe('modules/history/events/HistoryEventsView', () => {
  let wrapper: VueWrapper | undefined;

  function mountView(props: Record<string, unknown> = {}): VueWrapper {
    wrapper = mount(HistoryEventsView, {
      global: {
        stubs: {
          AccountingOverlayToggle: OverlayToggleStub,
          BalanceDivergenceToggle: true,
          HistoryEventsDialogContainer: DialogContainerStub,
          HistoryEventsFiltersChips: FiltersChipsStub,
          HistoryEventsTableActions: TableActionsStub,
          HistoryEventsViewButtons: ViewButtonsStub,
          HistoryEventsVirtualTable: VirtualTableStub,
          RefreshButton: true,
          SyncProgressPanel: true,
          TablePageLayout: TablePageLayoutStub,
        },
      },
      props,
    });
    return wrapper;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(processing, false);
    set(refreshing, false);
    set(overlayAvailable, false);
    set(duplicateHandlingStatus, undefined);
    set(groupIdentifiers, undefined);
    set(ignoreStatus, undefined);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  it('should title the page with the section it was given', () => {
    const view = mountView({ mainPage: true, sectionTitle: 'Trades' });

    expect(view.findComponent(TablePageLayoutStub).props('title'))
      .toStrictEqual(['navigation_menu.history', 'Trades']);
  });

  it('should fall back to the generic title', () => {
    const view = mountView({ mainPage: true });

    expect(view.findComponent(TablePageLayoutStub).props('title'))
      .toStrictEqual(['navigation_menu.history', 'transactions.title']);
  });

  it('should render as a child page, without the sync panel, when it is not the main page', () => {
    const view = mountView();

    const layout = view.findComponent(TablePageLayoutStub);
    expect(layout.props('child')).toBe(true);
    expect(layout.props('hideHeader')).toBe(true);
    expect(view.find('sync-progress-panel-stub').exists()).toBe(false);
  });

  it('should keep the redecode buttons off a child page', () => {
    const view = mountView();

    expect(view.findComponent(TableActionsStub).props('hideRedecodeButtons')).toBe(true);
  });

  it('should offer them on the main page', () => {
    const view = mountView({ mainPage: true });

    expect(view.findComponent(TableActionsStub).props('hideRedecodeButtons')).toBe(false);
  });

  describe('what the table is asked to load', () => {
    it('should hand it the source the projection built', () => {
      const view = mountView();

      const source = view.findComponent(VirtualTableStub).props('source');
      expect(source).toStrictEqual({
        excludeIgnored: true,
        groupLoading: false,
        groups: get(groups),
        identifiers: undefined,
        requestPayload: undefined,
      });
    });

    it('should show it as processing while either a fetch or a refresh runs', async () => {
      const view = mountView();
      expect(view.findComponent(VirtualTableStub).props('processing')).toBe(false);

      set(refreshing, true);
      await nextTick();

      expect(view.findComponent(VirtualTableStub).props('processing')).toBe(true);
    });
  });

  describe('the accounting overlay toggles', () => {
    it('should stay hidden while no overlay is available', () => {
      const view = mountView();

      expect(view.findComponent(OverlayToggleStub).exists()).toBe(false);
    });

    it('should appear once one is', async () => {
      const view = mountView();

      set(overlayAvailable, true);
      await nextTick();

      expect(view.findComponent(OverlayToggleStub).exists()).toBe(true);
    });
  });

  describe('where the table sends its events', () => {
    it('should clear the filters', async () => {
      const view = mountView();

      view.findComponent(VirtualTableStub).vm.$emit('clear-filters');
      await nextTick();

      expect(clearFilters).toHaveBeenCalledTimes(1);
    });

    it('should route a refresh through the page handler', async () => {
      const view = mountView();
      const payload = { transactions: [{ location: 'ethereum', txRef: '0xabc' }] };

      view.findComponent(VirtualTableStub).vm.$emit('refresh', payload);
      await nextTick();

      expect(handleRedecode).toHaveBeenCalledWith(payload);
    });

    it('should redecode a block event through the actions', async () => {
      const view = mountView();

      view.findComponent(VirtualTableStub).vm.$emit('refresh:block-event', { blockNumbers: [1] });
      await nextTick();

      expect(redecodeBlocks).toHaveBeenCalledWith({ blockNumbers: [1] });
    });

    it('should page and report its rendered events', async () => {
      const view = mountView();
      const table = view.findComponent(VirtualTableStub);
      const update = { eventIds: [1], groupedEvents: {} };

      table.vm.$emit('set-page', 2);
      table.vm.$emit('update-event-ids', update);
      await nextTick();

      expect(setPage).toHaveBeenCalledWith(2);
      expect(handleUpdateEventIds).toHaveBeenCalledWith(update);
    });
  });

  describe('where the toolbar sends its events', () => {
    it('should report a selection action', async () => {
      const view = mountView();

      view.findComponent(TableActionsStub).vm.$emit('selection:action', 'delete');
      await nextTick();

      expect(handleSelectionAction).toHaveBeenCalledWith('delete');
    });

    it('should route a filter change through the filters composable', async () => {
      const view = mountView();
      const actions = view.findComponent(TableActionsStub);

      actions.vm.$emit('update:action', 'deposit');
      actions.vm.$emit('update:locationLabels', ['kraken']);
      await nextTick();

      expect(onActionChanged).toHaveBeenCalledWith('deposit');
      expect(onLocationLabelsChanged).toHaveBeenCalledWith(['kraken']);
    });

    it('should redecode by the scope it was given', async () => {
      const view = mountView();

      view.findComponent(TableActionsStub).vm.$emit('redecode', 'all');
      await nextTick();

      expect(redecodeBy).toHaveBeenCalledWith('all');
    });

    it('should hand it the ignore counts the selection worked out', async () => {
      const view = mountView();

      set(ignoreStatus, { ignoredCount: 1, notIgnoredCount: 2 });
      await nextTick();

      expect(view.findComponent(TableActionsStub).props('ignoreStatus'))
        .toStrictEqual({ ignoredCount: 1, notIgnoredCount: 2 });
    });
  });

  describe('the filter chips', () => {
    it('should be handed the duplicate filter the URL pins', async () => {
      const view = mountView();

      set(groupIdentifiers, ['g1']);
      set(duplicateHandlingStatus, 'auto-fix');
      await nextTick();

      const chips = view.findComponent(FiltersChipsStub);
      expect(chips.props('groupIdentifiers')).toStrictEqual(['g1']);
      expect(chips.props('duplicateHandlingStatus')).toBe('auto-fix');
    });

    it('should reload the events when they ask for it', async () => {
      const view = mountView();

      view.findComponent(FiltersChipsStub).vm.$emit('refresh');
      await nextTick();

      expect(fetchDataAndLocations).toHaveBeenCalledTimes(1);
    });
  });

  describe('the dialog container', () => {
    it('should be handed the page handlers and the selected events', () => {
      const view = mountView();

      const container = view.findComponent(DialogContainerStub);
      expect(container.props('eventHandlers')).toBe(dialogHandlers);
      expect(container.props('selectedEventIds')).toStrictEqual([1, 2]);
    });

    it('should route each of its events to its own handler', async () => {
      const view = mountView();
      const container = view.findComponent(DialogContainerStub);

      container.vm.$emit('accounting-rule-refresh');
      container.vm.$emit('movement-matched');
      container.vm.$emit('bridge-matched');
      await nextTick();

      expect(handleAccountingRuleRefresh).toHaveBeenCalledTimes(1);
      expect(handleMovementChanged).toHaveBeenCalledTimes(1);
      expect(handleBridgeChanged).toHaveBeenCalledTimes(1);
    });
  });

  describe('the header buttons', () => {
    it('should refresh everything', async () => {
      const view = mountView({ mainPage: true });

      view.findComponent(ViewButtonsStub).vm.$emit('refresh', true);
      await nextTick();

      expect(refreshAll).toHaveBeenCalledWith(true, true);
    });

    it('should be told whether evm events are included', () => {
      const view = mountView({ mainPage: true });

      expect(view.findComponent(ViewButtonsStub).props('includeEvmEvents')).toBe(true);
    });
  });
});
