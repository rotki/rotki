import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { HighlightTargetTypes } from '@/modules/history/events/use-history-event-navigation';
import { usePinnedMatchPanel, type UsePinnedMatchPanelReturn } from '@/modules/history/events/use-pinned-match-panel';
import { PinnedNames } from '@/modules/session/types';

interface TestRow {
  groupIdentifier: string;
  identifier: number;
}

const routerReplace = vi.fn().mockResolvedValue(undefined);
const routeQuery = ref<Record<string, unknown>>({});

const { useRouteMock, useRouterMock } = vi.hoisted(() => ({
  useRouteMock: vi.fn(),
  useRouterMock: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRoute: useRouteMock,
  useRouter: useRouterMock,
}));

const clearHighlightTarget = vi.fn();
const requestNavigation = vi.fn();
const setHighlightTarget = vi.fn();

vi.mock('@/modules/history/events/use-history-event-navigation', async importOriginal => ({
  ...(await importOriginal<object>()),
  useHistoryEventNavigation: (): Record<string, unknown> => ({
    clearHighlightTarget,
    requestNavigation,
    setHighlightTarget,
  }),
}));

const clearHighlight = vi.fn().mockResolvedValue(undefined);
const pinnedReset = vi.fn();

vi.mock('@/modules/shell/pinned/use-pinned-highlight-navigation', () => ({
  usePinnedHighlightNavigation: (_keys: string[], reset: () => void): Record<string, unknown> => {
    pinnedReset.mockImplementation(reset);
    return { clearHighlight };
  },
}));

const unpinPanel = vi.fn();
const isPinned = ref<boolean>(true);

vi.mock('@/modules/shell/pinned/use-pinned-panel', () => ({
  usePinnedPanel: (): Record<string, unknown> => ({ isPinned, unpin: unpinPanel }),
}));

const unmatched = ref<TestRow[]>([]);
const ignored = ref<TestRow[]>([]);
const groupProp = ref<string | undefined>();
const matchProp = ref<number | undefined>();
const matchGroupProp = ref<string | undefined>();

interface Harness {
  wrapper: VueWrapper;
  panel: UsePinnedMatchPanelReturn<TestRow>;
}

function mountPanel(): Harness {
  let panel!: UsePinnedMatchPanelReturn<TestRow>;
  const Comp = defineComponent({
    setup(): () => null {
      panel = usePinnedMatchPanel<TestRow>({
        getIdentifier: row => row.identifier,
        highlightedGroupIdentifier: () => get(groupProp),
        highlightedPotentialMatchIdentifier: () => get(matchProp),
        pinnedName: PinnedNames.MATCH_ASSET_MOVEMENTS,
        potentialMatchGroupIdentifier: () => get(matchGroupProp),
        sources: [unmatched, ignored],
      });
      return (): null => null;
    },
  });
  const wrapper = mount(Comp);
  return { panel, wrapper };
}

const rowA: TestRow = { groupIdentifier: 'group-a', identifier: 11 };
const rowB: TestRow = { groupIdentifier: 'group-b', identifier: 22 };

describe('usePinnedMatchPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(routeQuery, {});
    set(unmatched, []);
    set(ignored, []);
    set(groupProp, undefined);
    set(matchProp, undefined);
    set(matchGroupProp, undefined);
    set(isPinned, true);
    useRouteMock.mockReturnValue(computed(() => ({ query: get(routeQuery) })));
    useRouterMock.mockReturnValue({ replace: routerReplace });
  });

  describe('selecting a row', () => {
    it('should open the drawer on the row and highlight it in the events table', () => {
      const { panel } = mountPanel();

      panel.select(rowA);

      expect(get(panel.subject)).toStrictEqual(rowA);
      expect(get(panel.modelSheetOpen)).toBe(true);
      expect(get(panel.activeGroupIdentifier)).toBe('group-a');
      expect(clearHighlightTarget).toHaveBeenCalledWith(HighlightTargetTypes.POTENTIAL_MATCH);
      expect(setHighlightTarget).toHaveBeenCalledWith(HighlightTargetTypes.ASSET_MOVEMENT, {
        groupIdentifier: 'group-a',
        identifier: 11,
      });
      expect(requestNavigation).toHaveBeenCalledWith({
        highlightedAssetMovement: 11,
        targetGroupIdentifier: 'group-a',
      });
    });

    it('should drop the green highlight of a previously selected row', () => {
      const { panel } = mountPanel();
      panel.showPotentialMatchInHistoryEvents({ groupIdentifier: 'group-a', identifier: 99 });
      expect(get(panel.activePotentialMatchIdentifier)).toBe(99);

      panel.select(rowA);

      expect(get(panel.activePotentialMatchIdentifier)).toBeUndefined();
    });

    it('should not open the drawer when only highlighting in the events table', () => {
      const { panel } = mountPanel();

      panel.showInHistoryEvents(rowA);

      expect(get(panel.subject)).toBeUndefined();
      expect(get(panel.modelSheetOpen)).toBe(false);
      expect(get(panel.activeGroupIdentifier)).toBe('group-a');
      expect(requestNavigation).toHaveBeenCalledWith({
        highlightedAssetMovement: 11,
        targetGroupIdentifier: 'group-a',
      });
    });
  });

  describe('the detail sheet model', () => {
    it('should stay closed until a row is actually selected', () => {
      const { panel } = mountPanel();

      expect(get(panel.modelSheetOpen)).toBe(false);
    });

    it('should close the drawer when written to false', async () => {
      const { panel } = mountPanel();
      panel.select(rowA);

      set(panel.modelSheetOpen, false);
      await nextTick();

      expect(get(panel.subject)).toBeUndefined();
      expect(get(panel.modelSheetOpen)).toBe(false);
    });

    it('should not close the drawer when written to true', async () => {
      const { panel } = mountPanel();
      panel.select(rowA);

      set(panel.modelSheetOpen, true);
      await nextTick();

      expect(get(panel.subject)).toStrictEqual(rowA);
      expect(get(panel.modelSheetOpen)).toBe(true);
    });
  });

  describe('closing the drawer', () => {
    it('should strip the green highlight from the route and keep the yellow one', async () => {
      set(routeQuery, { highlightedAssetMovement: '11', highlightedPotentialMatch: '99', tab: 'events' });
      const { panel } = mountPanel();
      panel.select(rowA);

      await panel.closeDrawer();

      expect(clearHighlightTarget).toHaveBeenCalledWith(HighlightTargetTypes.POTENTIAL_MATCH);
      expect(routerReplace).toHaveBeenCalledWith({
        query: { highlightedAssetMovement: '11', tab: 'events' },
      });
    });

    it('should leave the route alone when no green highlight is in it', async () => {
      set(routeQuery, { highlightedAssetMovement: '11' });
      const { panel } = mountPanel();
      panel.select(rowA);

      await panel.closeDrawer();

      expect(routerReplace).not.toHaveBeenCalled();
    });

    it('should clear every highlight after a match was made', async () => {
      const { panel } = mountPanel();
      panel.select(rowA);

      await panel.onMatched();

      expect(get(panel.subject)).toBeUndefined();
      expect(clearHighlight).toHaveBeenCalledTimes(1);
    });
  });

  describe('unpinning', () => {
    it('should clear the highlight before removing the tab', async () => {
      const { panel } = mountPanel();

      await panel.unpin();

      expect(clearHighlight).toHaveBeenCalledTimes(1);
      expect(unpinPanel).toHaveBeenCalledTimes(1);
      expect(clearHighlight.mock.invocationCallOrder[0])
        .toBeLessThan(unpinPanel.mock.invocationCallOrder[0]);
    });

    it('should reset the local highlight state when the shared teardown resets', () => {
      const { panel } = mountPanel();
      panel.select(rowA);

      pinnedReset();

      expect(get(panel.activeGroupIdentifier)).toBeUndefined();
      expect(get(panel.activePotentialMatchIdentifier)).toBeUndefined();
    });
  });

  describe('highlighting a potential match', () => {
    it('should keep the row highlight it is given', () => {
      const { panel } = mountPanel();

      panel.showPotentialMatchInHistoryEvents({ groupIdentifier: 'group-a', identifier: 99 }, 11);

      expect(get(panel.activePotentialMatchIdentifier)).toBe(99);
      expect(setHighlightTarget).toHaveBeenCalledWith(HighlightTargetTypes.POTENTIAL_MATCH, {
        groupIdentifier: 'group-a',
        identifier: 99,
      });
      expect(requestNavigation).toHaveBeenCalledWith({
        highlightedAssetMovement: 11,
        highlightedPotentialMatch: 99,
        targetGroupIdentifier: 'group-a',
      });
    });

    it('should fall back to the row highlight in the route', () => {
      set(routeQuery, { highlightedAssetMovement: '42' });
      const { panel } = mountPanel();

      panel.showPotentialMatchInHistoryEvents({ groupIdentifier: 'group-a', identifier: 99 });

      expect(requestNavigation).toHaveBeenCalledWith({
        highlightedAssetMovement: 42,
        highlightedPotentialMatch: 99,
        targetGroupIdentifier: 'group-a',
      });
    });

    it('should send no row highlight when the route carries none', () => {
      set(routeQuery, { highlightedAssetMovement: 'not-a-number' });
      const { panel } = mountPanel();

      panel.showPotentialMatchInHistoryEvents({ groupIdentifier: 'group-a', identifier: 99 });

      expect(requestNavigation).toHaveBeenCalledWith({
        highlightedAssetMovement: undefined,
        highlightedPotentialMatch: 99,
        targetGroupIdentifier: 'group-a',
      });
    });
  });

  describe('navigating to the requested highlight', () => {
    it('should wait for the row to arrive before navigating', async () => {
      set(groupProp, 'group-b');
      mountPanel();

      expect(requestNavigation).not.toHaveBeenCalled();

      set(unmatched, [rowA, rowB]);
      await nextTick();

      expect(requestNavigation).toHaveBeenCalledWith({
        highlightedAssetMovement: 22,
        targetGroupIdentifier: 'group-b',
      });
    });

    it('should navigate only once as more rows arrive', async () => {
      set(groupProp, 'group-a');
      mountPanel();

      set(unmatched, [rowA]);
      await nextTick();
      set(unmatched, [rowA, rowB]);
      await nextTick();

      expect(requestNavigation).toHaveBeenCalledTimes(1);
    });

    it('should search the later sources when the first misses', async () => {
      set(groupProp, 'group-b');
      mountPanel();

      set(unmatched, [rowA]);
      set(ignored, [rowB]);
      await nextTick();

      expect(requestNavigation).toHaveBeenCalledWith({
        highlightedAssetMovement: 22,
        targetGroupIdentifier: 'group-b',
      });
    });

    it('should not navigate when no highlight was requested', async () => {
      mountPanel();

      set(unmatched, [rowA, rowB]);
      await nextTick();

      expect(requestNavigation).not.toHaveBeenCalled();
    });

    it('should open the drawer on the row when a potential match is requested too', async () => {
      set(groupProp, 'group-a');
      set(matchProp, 99);
      set(matchGroupProp, 'group-c');
      const { panel } = mountPanel();

      set(unmatched, [rowA]);
      await nextTick();

      expect(get(panel.subject)).toStrictEqual(rowA);
      expect(get(panel.modelSheetOpen)).toBe(true);
      expect(get(panel.activeGroupIdentifier)).toBe('group-a');
      expect(requestNavigation).toHaveBeenCalledWith({
        highlightedAssetMovement: 11,
        highlightedPotentialMatch: 99,
        targetGroupIdentifier: 'group-c',
      });
    });

    it('should navigate again when the requested group changes', async () => {
      set(groupProp, 'group-a');
      set(unmatched, [rowA, rowB]);
      const { panel } = mountPanel();
      await nextTick();
      requestNavigation.mockClear();

      set(groupProp, 'group-b');
      await nextTick();

      expect(get(panel.activeGroupIdentifier)).toBe('group-b');
      expect(requestNavigation).toHaveBeenCalledWith({
        highlightedAssetMovement: 22,
        targetGroupIdentifier: 'group-b',
      });
    });

    it('should not navigate when the requested group is cleared', async () => {
      set(groupProp, 'group-a');
      set(unmatched, [rowA, rowB]);
      mountPanel();
      await nextTick();
      requestNavigation.mockClear();

      set(groupProp, undefined);
      await nextTick();

      expect(requestNavigation).not.toHaveBeenCalled();
    });
  });
});
