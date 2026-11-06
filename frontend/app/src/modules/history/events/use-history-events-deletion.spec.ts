import type { TransactionGroup } from './use-event-analysis';
import type { ConfirmChoice } from '@/modules/core/common/use-confirm-store';
import type { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryEventsActionFailure } from './use-history-events-action-failure';
import { useHistoryEventsDeletion } from './use-history-events-deletion';
import { useHistoryEventsSelectionMode } from './use-selection-mode';

const { spies } = vi.hoisted(() => ({
  spies: {
    ask: vi.fn<(message: object) => Promise<ConfirmChoice>>(),
    deleteHistoryEventApi: vi.fn(),
    deleteTransactions: vi.fn(),
    deleteHistoryEvent: vi.fn(),
    ignoreSingle: vi.fn(),
    getChain: vi.fn((chain: string) => chain),
    analyzeSelectedEvents: vi.fn(),
  },
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): object => ({ ask: spies.ask }),
}));
vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({ getChain: spies.getChain }),
}));
vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: (): ReturnType<typeof useHistoryEventsApi> => createMock<ReturnType<typeof useHistoryEventsApi>>({ deleteHistoryEvent: spies.deleteHistoryEventApi, deleteTransactions: spies.deleteTransactions }),
}));
vi.mock('@/modules/history/events/use-history-events', () => ({
  useHistoryEvents: (): object => ({ deleteHistoryEvent: spies.deleteHistoryEvent }),
}));
vi.mock('@/modules/history/use-ignore', () => ({
  useIgnore: (): object => ({ ignoreSingle: spies.ignoreSingle }),
}));
vi.mock('./use-event-analysis', () => ({
  analyzeSelectedEvents: spies.analyzeSelectedEvents,
}));

function txGroup(chain: string, groupIdentifier: string, events: number[]): TransactionGroup {
  return { chain, events, groupIdentifier };
}

function setup(requestPayload?: HistoryEventRequestPayload): {
  deletion: ReturnType<typeof useHistoryEventsDeletion>;
  selectionMode: ReturnType<typeof useHistoryEventsSelectionMode>;
  refreshCallback: ReturnType<typeof vi.fn>;
} {
  const selectionMode = useHistoryEventsSelectionMode();
  const refreshCallback = vi.fn().mockResolvedValue(undefined);
  const deletion = useHistoryEventsDeletion(
    selectionMode,
    ref<Record<string, HistoryEventRow[]>>({}),
    ref<HistoryEventRow[]>([]),
    refreshCallback,
    requestPayload ? computed<HistoryEventRequestPayload>(() => requestPayload) : undefined,
  );
  return { deletion, refreshCallback, selectionMode };
}

/** Queues how each confirmation the deletion raises gets answered, in order. */
function answer(...choices: ConfirmChoice[]): void {
  for (const choice of choices)
    spies.ask.mockResolvedValueOnce(choice);
}

const { actionFailure, clearActionFailure, reportActionFailure } = useHistoryEventsActionFailure();

describe('useHistoryEventsDeletion', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    clearActionFailure();
    spies.deleteHistoryEvent.mockResolvedValue({ success: true });
    spies.deleteHistoryEventApi.mockResolvedValue(true);
    spies.deleteTransactions.mockResolvedValue(undefined);
    spies.analyzeSelectedEvents.mockReturnValue({ completeTransactions: new Map(), partialEventIds: [], partialSwapGroups: [] });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should do nothing when the selection is empty', async () => {
    const { deletion } = setup();
    await deletion.deleteSelected();
    expect(spies.ask).not.toHaveBeenCalled();
    expect(get(deletion.isDeleting)).toBe(false);
  });

  describe('select all matching', () => {
    function selectAllMatching(): ReturnType<typeof setup> {
      const context = setup({
        aggregateByGroupIds: true,
        ascending: [true],
        limit: 10,
        notesSubstring: 'needle',
        offset: 0,
        onlyCache: true,
      });
      context.selectionMode.actions.toggleSelectAllMatching();
      context.selectionMode.setTotalMatchingCount(42);
      return context;
    }

    it('should delete by filter once confirmed, without the pagination and sort keys', async () => {
      answer('confirm');
      const { deletion, refreshCallback } = selectAllMatching();

      await deletion.deleteSelected();

      expect(spies.ask).toHaveBeenCalledOnce();
      expect(spies.deleteHistoryEventApi).toHaveBeenCalledWith({ notesSubstring: 'needle' }, true);
      expect(get(actionFailure)).toBeUndefined();
      expect(refreshCallback).toHaveBeenCalledOnce();
      expect(get(deletion.isDeleting)).toBe(false);
    });

    it('should name a refused filter delete above the table and keep the selection', async () => {
      answer('confirm');
      spies.deleteHistoryEventApi.mockResolvedValue(false);
      const { deletion, refreshCallback, selectionMode } = selectAllMatching();

      await deletion.deleteSelected();

      expect(get(actionFailure)).toEqual({ failure: 'transactions.events.delete.error.message', title: 'transactions.events.delete.error.title' });
      expect(get(selectionMode.isSelectAllMatching)).toBe(true);
      expect(refreshCallback).not.toHaveBeenCalled();
    });

    it('should settle without deleting when cancelled', async () => {
      answer('dismiss');
      const { deletion } = selectAllMatching();

      await deletion.deleteSelected();

      expect(spies.deleteHistoryEventApi).not.toHaveBeenCalled();
      expect(get(deletion.isDeleting)).toBe(false);
    });
  });

  it('should delete partial events through the confirmation', async () => {
    answer('confirm');
    spies.analyzeSelectedEvents.mockReturnValue({ completeTransactions: new Map(), partialEventIds: [1, 2], partialSwapGroups: [] });
    const { deletion, refreshCallback, selectionMode } = setup();
    selectionMode.actions.toggleEvent(1);
    selectionMode.actions.toggleEvent(2);

    await deletion.deleteSelected();

    expect(spies.deleteHistoryEvent).toHaveBeenCalledWith([1, 2], false);
    expect(get(actionFailure)).toBeUndefined();
    expect(refreshCallback).toHaveBeenCalledOnce();
  });

  it('should settle without deleting partial events when cancelled', async () => {
    answer('dismiss');
    spies.analyzeSelectedEvents.mockReturnValue({ completeTransactions: new Map(), partialEventIds: [1], partialSwapGroups: [] });
    const { deletion, selectionMode } = setup();
    selectionMode.actions.toggleEvent(1);

    await deletion.deleteSelected();

    expect(spies.deleteHistoryEvent).not.toHaveBeenCalled();
    expect(get(deletion.isDeleting)).toBe(false);
  });

  it('should name a failed partial event delete above the table', async () => {
    answer('confirm');
    spies.deleteHistoryEvent.mockResolvedValue({ message: 'nope', success: false });
    spies.analyzeSelectedEvents.mockReturnValue({ completeTransactions: new Map(), partialEventIds: [1], partialSwapGroups: [] });
    const { deletion, refreshCallback, selectionMode } = setup();
    selectionMode.actions.toggleEvent(1);

    await deletion.deleteSelected();

    expect(get(actionFailure)).toEqual({ failure: 'nope', title: 'transactions.events.delete.error.title' });
    expect(refreshCallback).not.toHaveBeenCalled();
  });

  it('should drop the last failure when the next delete starts', async () => {
    reportActionFailure('transactions.events.delete.error.title', 'nope');
    answer('dismiss');
    spies.analyzeSelectedEvents.mockReturnValue({ completeTransactions: new Map(), partialEventIds: [1], partialSwapGroups: [] });
    const { deletion, selectionMode } = setup();
    selectionMode.actions.toggleEvent(1);

    await deletion.deleteSelected();

    expect(get(actionFailure)).toBeUndefined();
  });

  describe('complete transactions', () => {
    function selectTransaction(): ReturnType<typeof setup> {
      const transactions = new Map([['0xabc', txGroup('ethereum', 'g1', [1, 2])]]);
      spies.analyzeSelectedEvents.mockReturnValue({ completeTransactions: transactions, partialEventIds: [], partialSwapGroups: [] });
      const context = setup();
      context.selectionMode.actions.toggleEvent(1);
      return context;
    }

    it('should delete them when the user confirms', async () => {
      answer('confirm');
      const { deletion, refreshCallback } = selectTransaction();

      await deletion.deleteSelected();

      expect(spies.deleteTransactions).toHaveBeenCalledWith('ethereum', '0xabc');
      expect(get(actionFailure)).toBeUndefined();
      expect(refreshCallback).toHaveBeenCalledOnce();
    });

    it('should close the prompt without offering to exclude when the user backs out', async () => {
      answer('dismiss');
      const { deletion } = selectTransaction();

      await deletion.deleteSelected();

      expect(spies.ask).toHaveBeenCalledOnce();
      expect(spies.deleteTransactions).not.toHaveBeenCalled();
      expect(get(deletion.isDeleting)).toBe(false);
    });

    it('should offer excluding from accounting as its own choice, which asks before excluding', async () => {
      answer('alternative', 'confirm');
      const { deletion } = selectTransaction();

      await deletion.deleteSelected();

      expect(spies.ask).toHaveBeenCalledTimes(2);
      expect(spies.ask.mock.calls[0][0]).toMatchObject({ alternativeAction: 'transactions.events.confirmation.ignore.action_short' });
      expect(spies.ask.mock.calls[1][0]).toMatchObject({ title: 'transactions.events.confirmation.ignore.title' });
      expect(spies.deleteTransactions).not.toHaveBeenCalled();
    });

    it('should report a failed exclusion instead of success', async () => {
      answer('alternative', 'confirm');
      spies.ignoreSingle.mockResolvedValue({ message: 'boom', success: false });
      const groupedEvents: Record<string, HistoryEventRow[]> = { g1: [createMock<HistoryEventEntry>({ identifier: 1 })] };
      const transactions = new Map([['0xabc', txGroup('ethereum', 'g1', [1])]]);
      spies.analyzeSelectedEvents.mockReturnValue({ completeTransactions: transactions, partialEventIds: [], partialSwapGroups: [] });
      const selectionMode = useHistoryEventsSelectionMode();
      const refreshCallback = vi.fn().mockResolvedValue(undefined);
      const deletion = useHistoryEventsDeletion(selectionMode, ref(groupedEvents), ref<HistoryEventRow[]>([]), refreshCallback);
      selectionMode.actions.toggleEvent(1);

      await deletion.deleteSelected();

      expect(spies.ignoreSingle).toHaveBeenCalledOnce();
      expect(get(actionFailure)).toEqual({ failure: 'boom', title: 'transactions.events.ignore.error.title' });
      expect(refreshCallback).not.toHaveBeenCalled();
    });

    it('should settle when the exclude question is cancelled', async () => {
      answer('alternative', 'dismiss');
      const { deletion } = selectTransaction();

      await deletion.deleteSelected();

      expect(spies.ignoreSingle).not.toHaveBeenCalled();
      expect(get(deletion.isDeleting)).toBe(false);
    });
  });

  it('should delete partial swap groups plus remaining events', async () => {
    answer('confirm');
    spies.analyzeSelectedEvents.mockReturnValue({
      completeTransactions: new Map(),
      partialEventIds: [9],
      partialSwapGroups: [{ groupIds: [1, 2], selectedIds: [1] }],
    });
    const { deletion, refreshCallback, selectionMode } = setup();
    selectionMode.actions.toggleEvent(1);

    await deletion.deleteSelected();

    // full swap group ids (1,2) plus remaining event (9)
    expect(spies.deleteHistoryEvent).toHaveBeenCalledWith([1, 2, 9], false);
    expect(refreshCallback).toHaveBeenCalledOnce();
  });

  it('should settle without deleting a partial swap when cancelled', async () => {
    answer('dismiss');
    spies.analyzeSelectedEvents.mockReturnValue({
      completeTransactions: new Map(),
      partialEventIds: [],
      partialSwapGroups: [{ groupIds: [1, 2], selectedIds: [1] }],
    });
    const { deletion, selectionMode } = setup();
    selectionMode.actions.toggleEvent(1);

    await deletion.deleteSelected();

    expect(spies.deleteHistoryEvent).not.toHaveBeenCalled();
    expect(get(deletion.isDeleting)).toBe(false);
  });
});
