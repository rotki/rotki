import type { TransactionGroup } from './use-event-analysis';
import type { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryEventsDeletion } from './use-history-events-deletion';
import { useHistoryEventsSelectionMode } from './use-selection-mode';

const { spies } = vi.hoisted(() => ({
  spies: {
    showConfirm: vi.fn(),
    showErrorMessage: vi.fn(),
    showSuccessMessage: vi.fn(),
    deleteHistoryEventApi: vi.fn(),
    deleteTransactions: vi.fn(),
    deleteHistoryEvent: vi.fn(),
    ignoreSingle: vi.fn(),
    getChain: vi.fn((chain: string) => chain),
    analyzeSelectedEvents: vi.fn(),
  },
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): object => ({ show: spies.showConfirm }),
}));
vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({ getChain: spies.getChain }),
}));
vi.mock('@/modules/core/notifications/use-notifications', async () => ({
  getErrorMessage: (await vi.importActual<typeof import('@/modules/core/common/logging/error-handling')>(
    '@/modules/core/common/logging/error-handling',
  )).getErrorMessage,
  useNotifications: (): object => ({ showErrorMessage: spies.showErrorMessage, showSuccessMessage: spies.showSuccessMessage }),
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

/**
 * Answers the confirm dialog a deletion is waiting on, then awaits the deletion itself.
 *
 * @param run - the deletion call, started but not awaited, since it settles only once answered
 * @param index - argument position of the callback in `show(message, onConfirm, onDismiss)`, so
 * 1 confirms and 2 dismisses
 */
async function drive(run: Promise<void>, index = 1): Promise<void> {
  await spies.showConfirm.mock.calls[0][index]();
  await run;
}

describe('useHistoryEventsDeletion', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
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
    expect(spies.showConfirm).not.toHaveBeenCalled();
    expect(get(deletion.isDeleting)).toBe(false);
  });

  it('should delete by filter when select-all-matching is active', async () => {
    const { deletion, refreshCallback, selectionMode } = setup({
      aggregateByGroupIds: true,
      ascending: [true],
      limit: 10,
      notesSubstring: 'needle',
      offset: 0,
      onlyCache: true,
    });
    selectionMode.actions.toggleSelectAllMatching();
    selectionMode.setTotalMatchingCount(42);

    const run = deletion.deleteSelected();
    expect(spies.showConfirm).toHaveBeenCalledOnce();

    await drive(run);
    // pagination/sort keys are stripped before the filter delete
    expect(spies.deleteHistoryEventApi).toHaveBeenCalledWith({ notesSubstring: 'needle' }, true);
    expect(spies.showSuccessMessage).toHaveBeenCalledOnce();
    expect(refreshCallback).toHaveBeenCalledOnce();
    expect(get(deletion.isDeleting)).toBe(false);
  });

  it('should delete partial events through the confirmation', async () => {
    spies.analyzeSelectedEvents.mockReturnValue({ completeTransactions: new Map(), partialEventIds: [1, 2], partialSwapGroups: [] });
    const { deletion, refreshCallback, selectionMode } = setup();
    selectionMode.actions.toggleEvent(1);
    selectionMode.actions.toggleEvent(2);

    await drive(deletion.deleteSelected());

    expect(spies.deleteHistoryEvent).toHaveBeenCalledWith([1, 2], false);
    expect(spies.showSuccessMessage).toHaveBeenCalledOnce();
    expect(refreshCallback).toHaveBeenCalledOnce();
  });

  it('should surface an error when partial event deletion fails', async () => {
    spies.deleteHistoryEvent.mockResolvedValue({ message: 'nope', success: false });
    spies.analyzeSelectedEvents.mockReturnValue({ completeTransactions: new Map(), partialEventIds: [1], partialSwapGroups: [] });
    const { deletion, refreshCallback, selectionMode } = setup();
    selectionMode.actions.toggleEvent(1);

    await drive(deletion.deleteSelected());

    expect(spies.showErrorMessage).toHaveBeenCalledOnce();
    expect(refreshCallback).not.toHaveBeenCalled();
  });

  it('should delete complete transactions and expose a secondary ignore option', async () => {
    const transactions = new Map([['0xabc', txGroup('ethereum', 'g1', [1, 2])]]);
    spies.analyzeSelectedEvents.mockReturnValue({ completeTransactions: transactions, partialEventIds: [], partialSwapGroups: [] });
    const { deletion, refreshCallback, selectionMode } = setup();
    selectionMode.actions.toggleEvent(1);

    const run = deletion.deleteSelected();
    // primary + secondary callbacks are both registered
    expect(spies.showConfirm.mock.calls[0]).toHaveLength(3);

    await drive(run);
    expect(spies.deleteTransactions).toHaveBeenCalledWith('ethereum', '0xabc');
    expect(spies.showSuccessMessage).toHaveBeenCalledOnce();
    expect(refreshCallback).toHaveBeenCalledOnce();
  });

  it('should delete partial swap groups plus remaining events', async () => {
    spies.analyzeSelectedEvents.mockReturnValue({
      completeTransactions: new Map(),
      partialEventIds: [9],
      partialSwapGroups: [{ groupIds: [1, 2], selectedIds: [1] }],
    });
    const { deletion, refreshCallback, selectionMode } = setup();
    selectionMode.actions.toggleEvent(1);

    await drive(deletion.deleteSelected());

    // full swap group ids (1,2) plus remaining event (9)
    expect(spies.deleteHistoryEvent).toHaveBeenCalledWith([1, 2, 9], false);
    expect(refreshCallback).toHaveBeenCalledOnce();
  });
});
