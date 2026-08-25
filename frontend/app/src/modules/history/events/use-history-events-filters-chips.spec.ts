import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import {
  useHistoryEventsFiltersChips,
  type UseHistoryEventsFiltersChipsReturn,
} from '@/modules/history/events/use-history-events-filters-chips';

const routerPush = vi.fn().mockResolvedValue(undefined);
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

const show = vi.fn();

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): Record<string, unknown> => ({ show }),
}));

const autoFixGroupIds = ref<string[]>([]);
const manualReviewGroupIds = ref<string[]>([]);
const fixLoading = ref<boolean>(false);
const fixDuplicates = vi.fn().mockResolvedValue({ success: true });

vi.mock('@/modules/history/events/use-customized-event-duplicates', () => ({
  useCustomizedEventDuplicates: (): Record<string, unknown> => ({
    autoFixGroupIds,
    fixDuplicates,
    fixLoading,
    manualReviewGroupIds,
  }),
}));

const groupIdentifiers = ref<string[] | undefined>();
const duplicateHandlingStatus = ref<DuplicateHandlingStatus | undefined>();
const onRefresh = vi.fn();

interface Harness {
  wrapper: VueWrapper;
  chips: UseHistoryEventsFiltersChipsReturn;
}

function mountChips(): Harness {
  let chips!: UseHistoryEventsFiltersChipsReturn;
  const Comp = defineComponent({
    setup(): () => null {
      chips = useHistoryEventsFiltersChips({
        duplicateHandlingStatus: () => get(duplicateHandlingStatus),
        groupIdentifiers: () => get(groupIdentifiers),
        onRefresh,
      });
      return (): null => null;
    },
  });
  const wrapper = mount(Comp);
  return { chips, wrapper };
}

describe('useHistoryEventsFiltersChips', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(routeQuery, {});
    set(autoFixGroupIds, []);
    set(manualReviewGroupIds, []);
    set(fixLoading, false);
    set(groupIdentifiers, undefined);
    set(duplicateHandlingStatus, undefined);
    fixDuplicates.mockResolvedValue({ success: true });
    routerPush.mockResolvedValue(undefined);
    routerReplace.mockResolvedValue(undefined);
    useRouteMock.mockReturnValue(computed(() => ({ query: get(routeQuery) })));
    useRouterMock.mockReturnValue({ push: routerPush, replace: routerReplace });
  });

  describe('which chips are shown', () => {
    it('should show nothing for an empty query', () => {
      const { chips } = mountChips();

      expect(get(chips.showMissingAcquisition)).toBe(false);
      expect(get(chips.showNegativeBalance)).toBe(false);
      expect(get(chips.showAccountingEvent)).toBe(false);
      expect(get(chips.showDuplicates)).toBe(false);
    });

    it('should show a chip for each filter the query carries', () => {
      set(routeQuery, {
        highlightedAccountingEvent: '3',
        highlightedNegativeBalanceEvent: '2',
        missingAcquisitionIdentifier: '1',
      });
      const { chips } = mountChips();

      expect(get(chips.showMissingAcquisition)).toBe(true);
      expect(get(chips.showNegativeBalance)).toBe(true);
      expect(get(chips.showAccountingEvent)).toBe(true);
    });

    it('should not show the duplicate chip for an empty group list', () => {
      set(groupIdentifiers, []);
      const { chips } = mountChips();

      expect(get(chips.showDuplicates)).toBe(false);
    });

    it('should show the duplicate chip once groups are pinned', () => {
      set(groupIdentifiers, ['g1']);
      const { chips } = mountChips();

      expect(get(chips.showDuplicates)).toBe(true);
    });

    it('should name the bucket the pinned groups came from', () => {
      set(groupIdentifiers, ['g1']);
      set(duplicateHandlingStatus, DuplicateHandlingStatus.AUTO_FIX);
      const { chips } = mountChips();

      expect(get(chips.isAutoFixable)).toBe(true);
      expect(get(chips.duplicateChipText)).toBe('customized_event_duplicates.chips.viewing_auto_fixable');

      set(duplicateHandlingStatus, DuplicateHandlingStatus.MANUAL_REVIEW);

      expect(get(chips.isAutoFixable)).toBe(false);
      expect(get(chips.duplicateChipText)).toBe('customized_event_duplicates.chips.viewing_manual_review');
    });
  });

  describe('closing a chip', () => {
    beforeEach(() => {
      set(routeQuery, {
        duplicateHandlingStatus: 'auto_fix',
        groupIdentifiers: 'g1',
        highlightedAccountingEvent: '3',
        highlightedNegativeBalanceEvent: '2',
        missingAcquisitionIdentifier: '1',
        targetGroupIdentifier: 'g1',
      });
    });

    it('should drop only the missing acquisition key', () => {
      const { chips } = mountChips();

      chips.removeMissingAcquisitionParam();

      expect(routerPush).toHaveBeenCalledWith({
        query: {
          duplicateHandlingStatus: 'auto_fix',
          groupIdentifiers: 'g1',
          highlightedAccountingEvent: '3',
          highlightedNegativeBalanceEvent: '2',
          targetGroupIdentifier: 'g1',
        },
      });
    });

    it('should drop the negative balance key and the group it targets', () => {
      const { chips } = mountChips();

      chips.removeNegativeBalanceParam();

      const [{ query }] = routerPush.mock.calls[0];
      expect(query).not.toHaveProperty('highlightedNegativeBalanceEvent');
      expect(query).not.toHaveProperty('targetGroupIdentifier');
      expect(query).toHaveProperty('highlightedAccountingEvent', '3');
    });

    it('should drop the accounting divergence key and the group it targets', () => {
      const { chips } = mountChips();

      chips.removeAccountingEventParam();

      const [{ query }] = routerPush.mock.calls[0];
      expect(query).not.toHaveProperty('highlightedAccountingEvent');
      expect(query).not.toHaveProperty('targetGroupIdentifier');
      expect(query).toHaveProperty('highlightedNegativeBalanceEvent', '2');
    });

    it('should drop both duplicate keys', () => {
      const { chips } = mountChips();

      chips.removeDuplicateEventsParam();

      const [{ query }] = routerPush.mock.calls[0];
      expect(query).not.toHaveProperty('groupIdentifiers');
      expect(query).not.toHaveProperty('duplicateHandlingStatus');
      expect(query).toHaveProperty('missingAcquisitionIdentifier', '1');
    });
  });

  describe('drift between the URL and the backend', () => {
    beforeEach(() => {
      set(duplicateHandlingStatus, DuplicateHandlingStatus.AUTO_FIX);
    });

    it('should report no drift while the two agree', () => {
      set(groupIdentifiers, ['g1', 'g2']);
      set(autoFixGroupIds, ['g1', 'g2']);
      const { chips } = mountChips();

      expect(get(chips.hasDuplicateChanges)).toBe(false);
      expect(get(chips.allDuplicatesResolved)).toBe(false);
      expect(get(chips.duplicateChangesMessage)).toBe('');
    });

    it('should count the pinned groups that are no longer duplicates', () => {
      set(groupIdentifiers, ['g1', 'g2']);
      set(autoFixGroupIds, ['g1']);
      const { chips } = mountChips();

      expect(get(chips.hasDuplicateChanges)).toBe(true);
      expect(get(chips.duplicateChangesMessage)).toBe('customized_event_duplicates.chips.resolved_count::1');
    });

    it('should count the duplicates that showed up after the URL was written', () => {
      set(groupIdentifiers, ['g1']);
      set(autoFixGroupIds, ['g1', 'g3']);
      const { chips } = mountChips();

      expect(get(chips.hasDuplicateChanges)).toBe(true);
      expect(get(chips.duplicateChangesMessage)).toBe('customized_event_duplicates.chips.added_count::1');
    });

    it('should report both counts at once', () => {
      set(groupIdentifiers, ['g1', 'g2']);
      set(autoFixGroupIds, ['g1', 'g3']);
      const { chips } = mountChips();

      expect(get(chips.duplicateChangesMessage))
        .toBe('customized_event_duplicates.chips.resolved_count::1 customized_event_duplicates.chips.added_count::1');
    });

    it('should say everything is resolved when nothing pinned is left', () => {
      set(groupIdentifiers, ['g1', 'g2']);
      set(autoFixGroupIds, []);
      const { chips } = mountChips();

      expect(get(chips.allDuplicatesResolved)).toBe(true);
      expect(get(chips.duplicateChangesMessage)).toBe('customized_event_duplicates.chips.all_resolved');
    });

    it('should read the manual review bucket when that is the one shown', () => {
      set(duplicateHandlingStatus, DuplicateHandlingStatus.MANUAL_REVIEW);
      set(groupIdentifiers, ['g1']);
      set(autoFixGroupIds, []);
      set(manualReviewGroupIds, ['g1']);
      const { chips } = mountChips();

      expect(get(chips.hasDuplicateChanges)).toBe(false);
      expect(get(chips.allDuplicatesResolved)).toBe(false);
    });

    it('should report no drift while nothing is pinned', () => {
      set(autoFixGroupIds, ['g1']);
      const { chips } = mountChips();

      expect(get(chips.hasDuplicateChanges)).toBe(false);
      expect(get(chips.allDuplicatesResolved)).toBe(false);
    });
  });

  describe('re-pointing the URL at the current duplicates', () => {
    beforeEach(() => {
      set(routeQuery, { duplicateHandlingStatus: 'auto_fix', groupIdentifiers: 'g1,g2' });
      set(duplicateHandlingStatus, DuplicateHandlingStatus.AUTO_FIX);
      set(groupIdentifiers, ['g1', 'g2']);
    });

    it('should replace the pinned groups with what is still a duplicate', () => {
      set(autoFixGroupIds, ['g1', 'g3']);
      const { chips } = mountChips();

      chips.refreshDuplicateView();

      expect(routerReplace).toHaveBeenCalledWith({
        query: { duplicateHandlingStatus: 'auto_fix', groupIdentifiers: 'g1,g3' },
      });
      expect(routerPush).not.toHaveBeenCalled();
      expect(onRefresh).toHaveBeenCalledTimes(1);
    });

    it('should drop the filter entirely when nothing is a duplicate any more', () => {
      set(autoFixGroupIds, []);
      const { chips } = mountChips();

      chips.refreshDuplicateView();

      expect(routerReplace).not.toHaveBeenCalled();
      const [{ query }] = routerPush.mock.calls[0];
      expect(query).not.toHaveProperty('groupIdentifiers');
      expect(onRefresh).toHaveBeenCalledTimes(1);
    });
  });

  describe('fixing the shown duplicates', () => {
    beforeEach(() => {
      set(routeQuery, { duplicateHandlingStatus: 'auto_fix', groupIdentifiers: 'g1,g2' });
      set(duplicateHandlingStatus, DuplicateHandlingStatus.AUTO_FIX);
      set(groupIdentifiers, ['g1', 'g2']);
    });

    async function confirmAndRun(chips: UseHistoryEventsFiltersChipsReturn): Promise<void> {
      chips.confirmFixDuplicate();
      const [, onConfirm] = show.mock.calls[0];
      await onConfirm();
    }

    it('should ask before fixing anything', () => {
      const { chips } = mountChips();

      chips.confirmFixDuplicate();

      const [message] = show.mock.calls[0];
      expect(message).toStrictEqual({
        message: 'customized_event_duplicates.actions.fix_selected_confirm::2',
        primaryAction: 'common.actions.confirm',
        title: 'customized_event_duplicates.actions.fix_selected',
      });
      expect(fixDuplicates).not.toHaveBeenCalled();
    });

    it('should clear the filter and reload once the fix succeeds', async () => {
      const { chips } = mountChips();

      await confirmAndRun(chips);

      expect(fixDuplicates).toHaveBeenCalledWith(['g1', 'g2']);
      expect(routerPush).toHaveBeenCalledTimes(1);
      expect(onRefresh).toHaveBeenCalledTimes(1);
    });

    it('should leave the filter alone when the fix fails', async () => {
      fixDuplicates.mockResolvedValue({ message: 'nope', success: false });
      const { chips } = mountChips();

      await confirmAndRun(chips);

      expect(routerPush).not.toHaveBeenCalled();
      expect(onRefresh).not.toHaveBeenCalled();
    });

    it('should not call the backend when nothing is pinned', async () => {
      set(groupIdentifiers, []);
      const { chips } = mountChips();

      await confirmAndRun(chips);

      expect(fixDuplicates).not.toHaveBeenCalled();
      expect(onRefresh).not.toHaveBeenCalled();
    });
  });
});
