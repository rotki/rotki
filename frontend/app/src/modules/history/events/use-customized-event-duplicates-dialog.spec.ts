import type { Collection } from '@/modules/core/common/collection';
import type { DuplicateRow, FetchDuplicateEventsPayload } from '@/modules/history/events/use-customized-event-duplicates';
import { Severity } from '@rotki/common';
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

type ConfirmMock = ReturnType<typeof vi.fn<(groupIdentifiers: string[], onSuccess?: () => void) => void>>;

const confirmAndFixDuplicate: ConfirmMock = vi.fn();
const confirmAndMarkNonDuplicated: ConfirmMock = vi.fn();
const confirmAndRestore: ConfirmMock = vi.fn();
const fetchCustomizedEventDuplicates = vi.fn<() => Promise<void>>();
const fetchDuplicateEvents = vi.fn<(payload: FetchDuplicateEventsPayload) => Promise<Collection<DuplicateRow>>>();

const autoFixGroupIds = ref<string[]>([]);
const manualReviewGroupIds = ref<string[]>([]);
const ignoredGroupIds = ref<string[]>([]);

const duplicatesApi = {
  autoFixGroupIds,
  confirmAndFixDuplicate,
  confirmAndMarkNonDuplicated,
  confirmAndRestore,
  fetchCustomizedEventDuplicates,
  fetchDuplicateEvents,
  ignoredGroupIds,
  manualReviewGroupIds,
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
   * Runs the callback the dialog handed to a confirmation, i.e. the user confirmed. The callback
   * starts the re-reads rather than awaiting them, so the promises are flushed here.
   */
  async function confirm(mock: ConfirmMock, call = 0): Promise<void> {
    const onSuccess = mock.mock.calls[call]?.[1];
    assert(onSuccess, 'no confirmation was requested');
    onSuccess();
    await flushPromises();
  }

  beforeEach(() => {
    vi.clearAllMocks();
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

    it('should notify and stop loading when the events cannot be read', async () => {
      fetchDuplicateEvents.mockRejectedValue(new Error('boom'));

      await dialog.initialize();

      expect(notify).toHaveBeenCalledTimes(3);
      expect(notify).toHaveBeenCalledWith(expect.objectContaining({
        display: true,
        severity: Severity.ERROR,
        title: 'actions.customized_event_duplicates.fetch_events_error.title',
      }));
      expect(get(dialog.autoFixRows)).toEqual([]);
      expect(get(dialog.autoFixLoading)).toBe(false);
      expect(get(dialog.manualReviewLoading)).toBe(false);
      expect(get(dialog.ignoredLoading)).toBe(false);
    });
  });

  describe('fixing', () => {
    it('should do nothing when nothing is selected', () => {
      dialog.fixSelected();

      expect(confirmAndFixDuplicate).not.toHaveBeenCalled();
    });

    it('should clear the selection and re-read only the auto-fix tab', async () => {
      set(dialog.modelSelectedAutoFix, ['auto-1', 'auto-2']);

      dialog.fixSelected();
      expect(confirmAndFixDuplicate).toHaveBeenCalledWith(['auto-1', 'auto-2'], expect.any(Function));

      await confirm(confirmAndFixDuplicate);

      expect(get(dialog.modelSelectedAutoFix)).toEqual([]);
      expect(fetchDuplicateEvents).toHaveBeenCalledOnce();
      expect(fetchDuplicateEvents).toHaveBeenCalledWith(expect.objectContaining({ groupIds: ['auto-1', 'auto-2'] }));
    });

    it('should drop only the fixed row from the selection', async () => {
      set(dialog.modelSelectedAutoFix, ['auto-1', 'auto-2']);

      dialog.fixSingle('auto-1');
      expect(confirmAndFixDuplicate).toHaveBeenCalledWith(['auto-1'], expect.any(Function));

      await confirm(confirmAndFixDuplicate);

      expect(get(dialog.modelSelectedAutoFix)).toEqual(['auto-2']);
    });
  });

  describe('marking as non-duplicated', () => {
    it('should drop the row from both actionable tabs and re-read all three', async () => {
      set(dialog.modelSelectedAutoFix, ['auto-1', 'shared']);
      set(dialog.modelSelectedManualReview, ['manual-1', 'shared']);

      dialog.ignoreSingle('shared');
      await confirm(confirmAndMarkNonDuplicated);

      expect(get(dialog.modelSelectedAutoFix)).toEqual(['auto-1']);
      expect(get(dialog.modelSelectedManualReview)).toEqual(['manual-1']);
      expect(fetchDuplicateEvents).toHaveBeenCalledTimes(3);
    });

    it('should act on the auto-fix selection while that tab is showing', async () => {
      set(dialog.modelSelectedAutoFix, ['auto-1']);
      set(dialog.modelSelectedManualReview, ['manual-1']);

      dialog.ignoreSelected();
      expect(confirmAndMarkNonDuplicated).toHaveBeenCalledWith(['auto-1'], expect.any(Function));

      await confirm(confirmAndMarkNonDuplicated);

      expect(get(dialog.modelSelectedAutoFix)).toEqual([]);
      expect(get(dialog.modelSelectedManualReview)).toEqual(['manual-1']);
    });

    it('should act on the manual review selection while that tab is showing', async () => {
      set(dialog.modelActiveTab, DuplicatesTab.MANUAL_REVIEW);
      set(dialog.modelSelectedAutoFix, ['auto-1']);
      set(dialog.modelSelectedManualReview, ['manual-1']);

      dialog.ignoreSelected();
      expect(confirmAndMarkNonDuplicated).toHaveBeenCalledWith(['manual-1'], expect.any(Function));

      await confirm(confirmAndMarkNonDuplicated);

      expect(get(dialog.modelSelectedManualReview)).toEqual([]);
      expect(get(dialog.modelSelectedAutoFix)).toEqual(['auto-1']);
    });

    it('should do nothing when the showing tab has no selection', () => {
      set(dialog.modelSelectedManualReview, ['manual-1']);

      dialog.ignoreSelected();

      expect(confirmAndMarkNonDuplicated).not.toHaveBeenCalled();
    });
  });

  describe('restoring', () => {
    it('should clear the ignored selection and re-read all three tabs', async () => {
      set(dialog.modelSelectedIgnored, ['ignored-1']);

      dialog.restoreSelected();
      expect(confirmAndRestore).toHaveBeenCalledWith(['ignored-1'], expect.any(Function));

      await confirm(confirmAndRestore);

      expect(get(dialog.modelSelectedIgnored)).toEqual([]);
      expect(fetchDuplicateEvents).toHaveBeenCalledTimes(3);
    });

    it('should drop only the restored row from the selection', async () => {
      set(dialog.modelSelectedIgnored, ['ignored-1', 'ignored-2']);

      dialog.restoreSingle('ignored-2');
      await confirm(confirmAndRestore);

      expect(get(dialog.modelSelectedIgnored)).toEqual(['ignored-1']);
    });

    it('should do nothing when nothing is selected', () => {
      dialog.restoreSelected();

      expect(confirmAndRestore).not.toHaveBeenCalled();
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
