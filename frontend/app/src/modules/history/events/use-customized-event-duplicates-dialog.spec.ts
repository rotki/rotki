import type { Collection } from '@/modules/core/common/collection';
import type { DuplicateRow, DuplicatesActionHandlers, FetchDuplicateEventsPayload } from '@/modules/history/events/use-customized-event-duplicates';
import { createMock } from '@test/utils/create-mock';
import { flushPromises } from '@vue/test-utils';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import { DuplicatesTab, useCustomizedEventDuplicatesDialog } from '@/modules/history/events/use-customized-event-duplicates-dialog';

const push = vi.fn();
vi.mock('vue-router', () => ({
  useRouter: (): { push: typeof push } => ({ push }),
}));

const notify = vi.fn();
vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: (): { notify: typeof notify } => ({ notify }),
}));

type SettleMock = ReturnType<typeof vi.fn<(groupIdentifiers: string[], handlers?: DuplicatesActionHandlers) => Promise<void>>>;

const fixAndSettle: SettleMock = vi.fn();
const markNonDuplicatedAndSettle: SettleMock = vi.fn();
const restoreAndSettle: SettleMock = vi.fn();
const fetchCustomizedEventDuplicates = vi.fn<() => Promise<void>>();
const fetchDuplicateEvents = vi.fn<(payload: FetchDuplicateEventsPayload) => Promise<Collection<DuplicateRow>>>();

const fetchError = shallowRef<unknown>();
const autoFixGroupIds = ref<string[]>([]);
const manualReviewGroupIds = ref<string[]>([]);
const ignoredGroupIds = ref<string[]>([]);

const duplicatesApi = {
  autoFixGroupIds,
  fetchCustomizedEventDuplicates,
  fetchDuplicateEvents,
  fetchError,
  fixAndSettle,
  ignoredGroupIds,
  manualReviewGroupIds,
  markNonDuplicatedAndSettle,
  restoreAndSettle,
};

vi.mock('@/modules/history/events/use-customized-event-duplicates', () => ({
  useCustomizedEventDuplicates: (): typeof duplicatesApi => duplicatesApi,
}));

function row(groupIdentifier: string): DuplicateRow {
  return {
    entry: createMock<DuplicateRow['entry']>({ groupIdentifier }),
    groupIdentifier,
    location: 'ethereum',
    locationLabel: null,
    timestamp: 1,
    txHash: '0xdead',
  };
}

function collection(data: DuplicateRow[]): Collection<DuplicateRow> {
  return { data, found: data.length, limit: data.length, total: data.length, totalValue: undefined };
}

/** The rows each group id was asked for, so a re-read can be told apart from the initial load. */
function rowsFor(payload: FetchDuplicateEventsPayload): Collection<DuplicateRow> {
  return collection(payload.groupIds.map(row));
}

describe('useCustomizedEventDuplicatesDialog', () => {
  const close = vi.fn();
  let dialog: ReturnType<typeof useCustomizedEventDuplicatesDialog>;

  /**
   * Runs the success handler the dialog handed to an action, i.e. the action went through. The
   * handler starts the re-reads rather than awaiting them, so the promises are flushed here.
   */
  async function succeed(mock: SettleMock, call = 0): Promise<void> {
    const onSuccess = mock.mock.calls[call]?.[1]?.onSuccess;
    assert(onSuccess, 'the action was not started');
    onSuccess();
    await flushPromises();
  }

  function fail(mock: SettleMock, failure: string, call = 0): void {
    const onFailure = mock.mock.calls[call]?.[1]?.onFailure;
    assert(onFailure, 'the action was not started');
    onFailure({ failure, title: 'title' });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(fetchError, undefined);
    set(autoFixGroupIds, ['auto-1', 'auto-2']);
    set(manualReviewGroupIds, ['manual-1']);
    set(ignoredGroupIds, ['ignored-1']);
    fetchDuplicateEvents.mockImplementation(async payload => rowsFor(payload));
    dialog = useCustomizedEventDuplicatesDialog({ close });
  });

  describe('initialize', () => {
    it('should read the group ids, then the events behind each tab', async () => {
      await dialog.initialize();

      expect(fetchCustomizedEventDuplicates).toHaveBeenCalledOnce();
      expect(fetchDuplicateEvents).toHaveBeenCalledTimes(3);
      expect(fetchDuplicateEvents).toHaveBeenCalledWith({ groupIds: ['auto-1', 'auto-2'], limit: 2, offset: 0 });
      expect(fetchDuplicateEvents).toHaveBeenCalledWith({ groupIds: ['manual-1'], limit: 1, offset: 0 });
      expect(fetchDuplicateEvents).toHaveBeenCalledWith({ groupIds: ['ignored-1'], limit: 1, offset: 0 });

      expect(get(dialog.autoFixRows).map(entry => entry.groupIdentifier)).toEqual(['auto-1', 'auto-2']);
      expect(get(dialog.manualReviewRows).map(entry => entry.groupIdentifier)).toEqual(['manual-1']);
      expect(get(dialog.ignoredRows).map(entry => entry.groupIdentifier)).toEqual(['ignored-1']);
      expect(get(dialog.autoFixLoading)).toBe(false);
    });

    it('should ask for a limit of one when a tab has no groups', async () => {
      set(manualReviewGroupIds, []);

      await dialog.initialize();

      expect(fetchDuplicateEvents).toHaveBeenCalledWith({ groupIds: [], limit: 1, offset: 0 });
    });

    it('should keep a failed read for each tab instead of a toast per tab, and stop loading', async () => {
      const failure = new Error('boom');
      fetchDuplicateEvents.mockRejectedValue(failure);

      await dialog.initialize();

      expect(notify).not.toHaveBeenCalled();
      expect(get(dialog.autoFixError)).toBe(failure);
      expect(get(dialog.manualReviewError)).toBe(failure);
      expect(get(dialog.ignoredError)).toBe(failure);
      expect(get(dialog.autoFixRows)).toEqual([]);
      expect(get(dialog.autoFixLoading)).toBe(false);
      expect(get(dialog.manualReviewLoading)).toBe(false);
      expect(get(dialog.ignoredLoading)).toBe(false);
    });

    it('should clear a tab\'s failure once a later read succeeds', async () => {
      fetchDuplicateEvents.mockRejectedValueOnce(new Error('boom'));
      await dialog.initialize();

      await dialog.initialize();

      expect(get(dialog.autoFixError)).toBeUndefined();
    });

    it('should show a failed read of the group ids on every tab', async () => {
      const failure = new Error('ids unavailable');
      set(fetchError, failure);

      await dialog.initialize();

      expect(get(dialog.autoFixError)).toBe(failure);
      expect(get(dialog.manualReviewError)).toBe(failure);
      expect(get(dialog.ignoredError)).toBe(failure);
    });
  });

  describe('retry', () => {
    it('should read only the failed tab again once the group ids are known', async () => {
      await dialog.initialize();
      vi.clearAllMocks();

      await dialog.retry(DuplicatesTab.MANUAL_REVIEW);

      expect(fetchCustomizedEventDuplicates).not.toHaveBeenCalled();
      expect(fetchDuplicateEvents).toHaveBeenCalledExactlyOnceWith({ groupIds: ['manual-1'], limit: 1, offset: 0 });
    });

    it('should read everything again when the group ids failed', async () => {
      set(fetchError, new Error('ids unavailable'));
      await dialog.initialize();
      vi.clearAllMocks();

      await dialog.retry(DuplicatesTab.MANUAL_REVIEW);

      expect(fetchCustomizedEventDuplicates).toHaveBeenCalledOnce();
      expect(fetchDuplicateEvents).toHaveBeenCalledTimes(3);
    });
  });

  describe('fixing', () => {
    it('should do nothing when nothing is selected', async () => {
      await dialog.fixSelected();

      expect(fixAndSettle).not.toHaveBeenCalled();
    });

    it('should clear the selection and re-read only the auto-fix tab', async () => {
      set(dialog.modelSelectedAutoFix, ['auto-1', 'auto-2']);

      await dialog.fixSelected();
      expect(fixAndSettle).toHaveBeenCalledWith(['auto-1', 'auto-2'], expect.any(Object));

      await succeed(fixAndSettle);

      expect(get(dialog.modelSelectedAutoFix)).toEqual([]);
      expect(fetchDuplicateEvents).toHaveBeenCalledOnce();
      expect(fetchDuplicateEvents).toHaveBeenCalledWith(expect.objectContaining({ groupIds: ['auto-1', 'auto-2'] }));
    });

    it('should drop only the fixed row from the selection', async () => {
      set(dialog.modelSelectedAutoFix, ['auto-1', 'auto-2']);

      await dialog.fixSingle('auto-1');
      expect(fixAndSettle).toHaveBeenCalledWith(['auto-1'], expect.any(Object));

      await succeed(fixAndSettle);

      expect(get(dialog.modelSelectedAutoFix)).toEqual(['auto-2']);
    });
  });

  describe('marking as non-duplicated', () => {
    it('should drop the row from both actionable tabs and re-read all three', async () => {
      set(dialog.modelSelectedAutoFix, ['auto-1', 'shared']);
      set(dialog.modelSelectedManualReview, ['manual-1', 'shared']);

      await dialog.ignoreSingle('shared');
      await succeed(markNonDuplicatedAndSettle);

      expect(get(dialog.modelSelectedAutoFix)).toEqual(['auto-1']);
      expect(get(dialog.modelSelectedManualReview)).toEqual(['manual-1']);
      expect(fetchDuplicateEvents).toHaveBeenCalledTimes(3);
    });

    it('should act on the auto-fix selection while that tab is showing', async () => {
      set(dialog.modelSelectedAutoFix, ['auto-1']);
      set(dialog.modelSelectedManualReview, ['manual-1']);

      await dialog.ignoreSelected();
      expect(markNonDuplicatedAndSettle).toHaveBeenCalledWith(['auto-1'], expect.any(Object));

      await succeed(markNonDuplicatedAndSettle);

      expect(get(dialog.modelSelectedAutoFix)).toEqual([]);
      expect(get(dialog.modelSelectedManualReview)).toEqual(['manual-1']);
    });

    it('should act on the manual review selection while that tab is showing', async () => {
      set(dialog.modelActiveTab, DuplicatesTab.MANUAL_REVIEW);
      set(dialog.modelSelectedAutoFix, ['auto-1']);
      set(dialog.modelSelectedManualReview, ['manual-1']);

      await dialog.ignoreSelected();
      expect(markNonDuplicatedAndSettle).toHaveBeenCalledWith(['manual-1'], expect.any(Object));

      await succeed(markNonDuplicatedAndSettle);

      expect(get(dialog.modelSelectedManualReview)).toEqual([]);
      expect(get(dialog.modelSelectedAutoFix)).toEqual(['auto-1']);
    });

    it('should do nothing when the showing tab has no selection', async () => {
      set(dialog.modelSelectedManualReview, ['manual-1']);

      await dialog.ignoreSelected();

      expect(markNonDuplicatedAndSettle).not.toHaveBeenCalled();
    });
  });

  describe('restoring', () => {
    it('should clear the ignored selection and re-read all three tabs', async () => {
      set(dialog.modelSelectedIgnored, ['ignored-1']);

      await dialog.restoreSelected();
      expect(restoreAndSettle).toHaveBeenCalledWith(['ignored-1'], expect.any(Object));

      await succeed(restoreAndSettle);

      expect(get(dialog.modelSelectedIgnored)).toEqual([]);
      expect(fetchDuplicateEvents).toHaveBeenCalledTimes(3);
    });

    it('should drop only the restored row from the selection', async () => {
      set(dialog.modelSelectedIgnored, ['ignored-1', 'ignored-2']);

      await dialog.restoreSingle('ignored-2');
      await succeed(restoreAndSettle);

      expect(get(dialog.modelSelectedIgnored)).toEqual(['ignored-1']);
    });

    it('should do nothing when nothing is selected', async () => {
      await dialog.restoreSelected();

      expect(restoreAndSettle).not.toHaveBeenCalled();
    });
  });

  describe('a failed action', () => {
    it('should stay on the tab it was started from', async () => {
      await dialog.fixSingle('auto-1');
      fail(fixAndSettle, 'boom');

      expect(get(dialog.autoFixActionFailure)).toEqual({ failure: 'boom', title: 'title' });
      expect(get(dialog.manualReviewActionFailure)).toBeUndefined();
      expect(get(dialog.modelSelectedAutoFix)).toEqual([]);
    });

    it('should land on the manual review tab when the dismissal was started there', async () => {
      set(dialog.modelActiveTab, DuplicatesTab.MANUAL_REVIEW);

      await dialog.ignoreSingle('manual-1');
      fail(markNonDuplicatedAndSettle, 'boom');

      expect(get(dialog.manualReviewActionFailure)).toEqual({ failure: 'boom', title: 'title' });
      expect(get(dialog.autoFixActionFailure)).toBeUndefined();
    });

    it('should land on the ignored tab for a failed restore', async () => {
      set(dialog.modelSelectedIgnored, ['ignored-1']);

      await dialog.restoreSelected();
      fail(restoreAndSettle, 'boom');

      expect(get(dialog.ignoredActionFailure)).toEqual({ failure: 'boom', title: 'title' });
    });

    it('should be dropped when the next action on that tab starts', async () => {
      await dialog.fixSingle('auto-1');
      fail(fixAndSettle, 'boom');

      await dialog.fixSingle('auto-2');

      expect(get(dialog.autoFixActionFailure)).toBeUndefined();
    });
  });

  describe('showInHistoryEvents', () => {
    it('should close the dialog and carry the groups into the query', async () => {
      await dialog.showInHistoryEvents(['auto-1', 'auto-2'], DuplicateHandlingStatus.AUTO_FIX);

      expect(close).toHaveBeenCalledOnce();
      expect(push).toHaveBeenCalledWith({
        name: '/history/events/',
        query: {
          duplicateHandlingStatus: DuplicateHandlingStatus.AUTO_FIX,
          groupIdentifiers: 'auto-1,auto-2',
        },
      });
    });

    it('should stay put when there are no groups to show', async () => {
      await dialog.showInHistoryEvents([], DuplicateHandlingStatus.IGNORED);

      expect(close).not.toHaveBeenCalled();
      expect(push).not.toHaveBeenCalled();
    });
  });
});
