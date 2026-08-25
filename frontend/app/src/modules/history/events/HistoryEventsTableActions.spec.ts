import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { UseHistoryEventsPillBarOptions } from '@/modules/history/events/use-history-events-pill-bar';
import type { SelectionState } from '@/modules/history/events/use-selection-mode';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import HistoryEventsTableActions from '@/modules/history/events/HistoryEventsTableActions.vue';

/**
 * The seam: the selection toolbar - which action each button reports, and the states in which
 * an action is refused. The bridge between the pill bar and the page's filter models lives in
 * `use-history-events-pill-bar`, which has its own spec.
 */

const pillBar = {
  applyView: vi.fn(),
  modelPillParams: ref<Record<string, unknown>>({}),
  pillLabels: ref({}),
  pillState: ref({ matches: {}, params: {} }),
  toggleMatchExact: vi.fn(),
};

let options: UseHistoryEventsPillBarOptions;

vi.mock('@/modules/history/events/use-history-events-pill-bar', () => ({
  useHistoryEventsPillBar: (opts: UseHistoryEventsPillBarOptions): unknown => {
    options = opts;
    return pillBar;
  },
}));

function passthrough(name: string, slots: string[] = []): ReturnType<typeof defineComponent> {
  return defineComponent({
    name,
    setup: (_props, context) => (): unknown => h('div', { 'data-testid': name }, [
      context.slots.default?.(),
      ...slots.map(slot => context.slots[slot]?.({ disabled: false })),
    ]),
  });
}

function leaf(name: string): ReturnType<typeof defineComponent> {
  return defineComponent({
    name,
    setup: () => (): unknown => h('div', { 'data-testid': name }),
  });
}

const HistoryTableActionsStub = passthrough('HistoryTableActions', ['filter']);
const PillFilterBarStub = passthrough('PillFilterBar', ['modifiers', 'views']);
const PillViewsMenuStub = leaf('PillViewsMenu');
const HistoryEventsExportStub = leaf('HistoryEventsExport');
const HistoryRedecodeButtonStub = defineComponent({
  emits: ['redecode'],
  name: 'HistoryRedecodeButton',
  setup: () => (): unknown => h('div', { 'data-testid': 'HistoryRedecodeButton' }),
});

function selectionState(overrides: Partial<SelectionState> = {}): SelectionState {
  return createMock<SelectionState>({
    hasAvailableEvents: true,
    isActive: true,
    isAllSelected: false,
    isPartiallySelected: false,
    selectAllMatching: false,
    selectedCount: 2,
    totalMatchingCount: 40,
    ...overrides,
  });
}

describe('modules/history/events/HistoryEventsTableActions', () => {
  let wrapper: VueWrapper | undefined;

  function mountActions(props: Record<string, unknown> = {}): VueWrapper {
    wrapper = mount(HistoryEventsTableActions, {
      global: {
        stubs: {
          HistoryEventsExport: HistoryEventsExportStub,
          HistoryRedecodeButton: HistoryRedecodeButtonStub,
          HistoryTableActions: HistoryTableActionsStub,
          PillFilterBar: PillFilterBarStub,
          PillViewsMenu: PillViewsMenuStub,
        },
      },
      props: {
        action: undefined,
        exportParams: createMock<HistoryEventRequestPayload>({}),
        fields: [],
        filters: {},
        locationLabels: [],
        selection: selectionState(),
        toggles: { matchExactEvents: false, showIgnoredAssets: false, stateMarkers: [] },
        ...props,
      },
    });
    return wrapper;
  }

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  it('should hand the page filter models to the pill bar bridge', () => {
    mountActions({ action: 'deposit', locationLabels: ['kraken'] });

    expect(get(options.action)).toBe('deposit');
    expect(get(options.locationLabels)).toStrictEqual(['kraken']);
    expect(get(options.toggles)).toStrictEqual({
      matchExactEvents: false,
      showIgnoredAssets: false,
      stateMarkers: [],
    });
  });

  it('should flip match exact through the bridge', async () => {
    const view = mountActions();

    await view.find('[data-testid="filter-match-exact"]').trigger('click');

    expect(pillBar.toggleMatchExact).toHaveBeenCalledTimes(1);
  });

  it('should show match exact as pressed when it is on', () => {
    const view = mountActions({ toggles: { matchExactEvents: true, showIgnoredAssets: false, stateMarkers: [] } });

    expect(view.find('[data-testid="filter-match-exact"]').attributes('aria-pressed')).toBe('true');
  });

  describe('the selection toolbar', () => {
    it.each([
      ['selection-delete', 'delete'],
      ['selection-ignore', 'ignore'],
      ['selection-unignore', 'unignore'],
      ['selection-create-rule', 'create-rule'],
      ['selection-exit', 'exit'],
      ['selection-select-all-matching', 'toggle-select-all-matching'],
    ] as const)('should report %s as a %s', async (testId, expected) => {
      const view = mountActions({ ignoreStatus: { ignoredCount: 1, notIgnoredCount: 1 } });

      await view.find(`[data-testid="${testId}"]`).trigger('click');

      expect(view.emitted('selection:action')).toStrictEqual([[expected]]);
    });

    it('should report the page checkbox as a toggle-all', async () => {
      const view = mountActions();

      // The test id falls through to the checkbox wrapper, so the input is what to click.
      await view.find('[data-testid="selection-select-all-page"] input').setValue(true);

      expect(view.emitted('selection:action')).toStrictEqual([['toggle-all']]);
    });

    it('should count what is selected', () => {
      const view = mountActions({ selection: selectionState({ selectedCount: 7 }) });

      expect(view.find('[data-testid="selection-count"]').text())
        .toBe('transactions.events.selection_mode.selected_count::7');
    });

    it.each([
      'selection-delete',
      'selection-ignore',
      'selection-unignore',
      'selection-create-rule',
    ])('should disable %s while nothing is selected', (testId) => {
      const view = mountActions({
        ignoreStatus: { ignoredCount: 1, notIgnoredCount: 1 },
        selection: selectionState({ selectedCount: 0 }),
      });

      expect(view.find(`[data-testid="${testId}"]`).attributes('disabled')).toBeDefined();
    });

    it('should refuse to ignore when nothing selected is still un-ignored', () => {
      const view = mountActions({ ignoreStatus: { ignoredCount: 2, notIgnoredCount: 0 } });

      expect(view.find('[data-testid="selection-ignore"]').attributes('disabled')).toBeDefined();
      expect(view.find('[data-testid="selection-unignore"]').attributes('disabled')).toBeUndefined();
    });

    it('should refuse to unignore when nothing selected is ignored', () => {
      const view = mountActions({ ignoreStatus: { ignoredCount: 0, notIgnoredCount: 2 } });

      expect(view.find('[data-testid="selection-unignore"]').attributes('disabled')).toBeDefined();
      expect(view.find('[data-testid="selection-ignore"]').attributes('disabled')).toBeUndefined();
    });

    it('should refuse both while the ignore counts are unknown', () => {
      const view = mountActions();

      expect(view.find('[data-testid="selection-ignore"]').attributes('disabled')).toBeDefined();
      expect(view.find('[data-testid="selection-unignore"]').attributes('disabled')).toBeDefined();
    });

    it('should drop the per-page controls once everything matching is selected', () => {
      const view = mountActions({
        ignoreStatus: { ignoredCount: 1, notIgnoredCount: 1 },
        selection: selectionState({ selectAllMatching: true }),
      });

      expect(view.find('[data-testid="selection-count"]').exists()).toBe(false);
      expect(view.find('[data-testid="selection-select-all-matching"]').text())
        .toContain('transactions.events.selection_mode.all_matching_selected::40');
      expect(view.find('[data-testid="selection-ignore"]').attributes('disabled')).toBeDefined();
      expect(view.find('[data-testid="selection-create-rule"]').attributes('disabled')).toBeDefined();
      expect(view.find('[data-testid="selection-delete"]').attributes('disabled')).toBeUndefined();
    });
  });

  describe('outside selection mode', () => {
    it('should offer the toolbar in its place', () => {
      const view = mountActions({ selection: selectionState({ isActive: false }) });

      expect(view.find('[data-testid="selection-delete"]').exists()).toBe(false);
      expect(view.findComponent(HistoryRedecodeButtonStub).exists()).toBe(true);
      expect(view.findComponent(HistoryEventsExportStub).exists()).toBe(true);
    });

    it('should enter selection mode', async () => {
      const view = mountActions({ selection: selectionState({ isActive: false }) });

      await view.find('[data-testid="selection-toggle-mode"]').trigger('click');

      expect(view.emitted('selection:action')).toStrictEqual([['toggle-mode']]);
    });

    it('should refuse to enter it with no events to select', () => {
      const view = mountActions({ selection: selectionState({ hasAvailableEvents: false, isActive: false }) });

      expect(view.find('[data-testid="selection-toggle-mode"]').attributes('disabled')).toBeDefined();
    });

    it('should hide the redecode button when the page asks it to', () => {
      const view = mountActions({
        hideRedecodeButtons: true,
        selection: selectionState({ isActive: false }),
      });

      expect(view.findComponent(HistoryRedecodeButtonStub).exists()).toBe(false);
    });

    it('should pass a redecode on to the page', async () => {
      const view = mountActions({ selection: selectionState({ isActive: false }) });

      view.findComponent(HistoryRedecodeButtonStub).vm.$emit('redecode', 'all');
      await nextTick();

      expect(view.emitted('redecode')).toStrictEqual([['all']]);
    });
  });
});
