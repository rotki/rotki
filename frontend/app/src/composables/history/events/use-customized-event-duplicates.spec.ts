import type { CustomizedEventDuplicates, CustomizedEventDuplicatesFixResult } from '@/composables/api/history/events/customized-event-duplicates';
import type { CollectionResponse } from '@/types/collection';
import type { HistoryEventCollectionRow, HistoryEventEntryWithMeta } from '@/types/history/events/schemas';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCustomizedEventDuplicates } from '@/composables/history/events/use-customized-event-duplicates';

const { spies } = vi.hoisted(() => ({
  spies: {
    getCustomizedEventDuplicates: vi.fn<() => Promise<CustomizedEventDuplicates>>(),
    fixCustomizedEventDuplicates: vi.fn<(groupIdentifiers?: string[]) => Promise<CustomizedEventDuplicatesFixResult>>(),
    ignoreCustomizedEventDuplicates: vi.fn<(groupIdentifiers: string[]) => Promise<string[]>>(),
    unignoreCustomizedEventDuplicates: vi.fn<(groupIdentifiers: string[]) => Promise<string[]>>(),
    fetchHistoryEvents: vi.fn<() => Promise<CollectionResponse<HistoryEventCollectionRow>>>(),
    showConfirm: vi.fn(),
    setMessage: vi.fn(),
  },
}));

vi.mock('@/composables/api/history/events/customized-event-duplicates', () => ({
  useCustomizedEventDuplicatesApi: (): object => ({
    getCustomizedEventDuplicates: spies.getCustomizedEventDuplicates,
    fixCustomizedEventDuplicates: spies.fixCustomizedEventDuplicates,
    ignoreCustomizedEventDuplicates: spies.ignoreCustomizedEventDuplicates,
    unignoreCustomizedEventDuplicates: spies.unignoreCustomizedEventDuplicates,
  }),
}));

vi.mock('@/composables/api/history/events', () => ({
  useHistoryEventsApi: (): object => ({
    fetchHistoryEvents: spies.fetchHistoryEvents,
  }),
}));

vi.mock('@/store/confirm', () => ({
  useConfirmStore: (): object => ({
    show: spies.showConfirm,
  }),
}));

vi.mock('@/store/message', () => ({
  useMessageStore: (): object => ({
    setMessage: spies.setMessage,
  }),
}));

function createMockEventRow(overrides: {
  groupIdentifier?: string;
  location?: string;
  locationLabel?: string | null;
  timestamp?: number;
  txRef?: string;
} = {}): HistoryEventEntryWithMeta {
  return {
    entry: {
      location: overrides.location ?? 'ethereum',
      locationLabel: overrides.locationLabel ?? '0xAddress',
      timestamp: overrides.timestamp ?? 1700000000,
      groupIdentifier: overrides.groupIdentifier ?? 'group-1',
      txRef: overrides.txRef ?? '0xTxHash',
    },
    eventAccountingRuleStatus: 'has_rule',
  } as unknown as HistoryEventEntryWithMeta;
}

function createMockDuplicatesResponse(autoFix: string[] = [], manualReview: string[] = [], ignored: string[] = []): CustomizedEventDuplicates {
  return {
    autoFixGroupIds: autoFix,
    manualReviewGroupIds: manualReview,
    ignoredGroupIds: ignored,
  };
}

async function extractAndCallConfirmCallback(): Promise<void> {
  const callback = spies.showConfirm.mock.calls[0][1] as () => Promise<void>;
  await callback();
}

describe('use-customized-event-duplicates', () => {
  let composable: ReturnType<typeof useCustomizedEventDuplicates>;

  beforeEach(async () => {
    vi.clearAllMocks();
    // Reset shared composable state
    spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());
    composable = useCustomizedEventDuplicates();
    await composable.fetchCustomizedEventDuplicates();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('initial state after reset', () => {
    it('should have zero counts', () => {
      expect(get(composable.autoFixCount)).toBe(0);
      expect(get(composable.manualReviewCount)).toBe(0);
      expect(get(composable.ignoredCount)).toBe(0);
      expect(get(composable.actionableCount)).toBe(0);
      expect(get(composable.totalCount)).toBe(0);
    });

    it('should have empty group IDs', () => {
      expect(get(composable.autoFixGroupIds)).toEqual([]);
      expect(get(composable.manualReviewGroupIds)).toEqual([]);
      expect(get(composable.ignoredGroupIds)).toEqual([]);
    });

    it('should have false loading states', () => {
      expect(get(composable.loading)).toBe(false);
      expect(get(composable.fixLoading)).toBe(false);
      expect(get(composable.ignoreLoading)).toBe(false);
    });
  });

  describe('fetchCustomizedEventDuplicates', () => {
    it('should populate group IDs on success', async () => {
      spies.getCustomizedEventDuplicates.mockResolvedValue(
        createMockDuplicatesResponse(['af-1', 'af-2'], ['mr-1'], ['ig-1', 'ig-2', 'ig-3']),
      );

      await composable.fetchCustomizedEventDuplicates();

      expect(get(composable.autoFixGroupIds)).toEqual(['af-1', 'af-2']);
      expect(get(composable.manualReviewGroupIds)).toEqual(['mr-1']);
      expect(get(composable.ignoredGroupIds)).toEqual(['ig-1', 'ig-2', 'ig-3']);
    });

    it('should set loading during fetch', async () => {
      const loadingDuringCall: boolean[] = [];
      spies.getCustomizedEventDuplicates.mockImplementation(async () => {
        loadingDuringCall.push(get(composable.loading));
        return createMockDuplicatesResponse();
      });

      await composable.fetchCustomizedEventDuplicates();

      expect(loadingDuringCall[0]).toBe(true);
      expect(get(composable.loading)).toBe(false);
    });

    it('should reset loading on error', async () => {
      spies.getCustomizedEventDuplicates.mockRejectedValue(new Error('Network error'));

      await composable.fetchCustomizedEventDuplicates();

      expect(get(composable.loading)).toBe(false);
    });

    it('should show error message on failure', async () => {
      spies.getCustomizedEventDuplicates.mockRejectedValue(new Error('Network error'));

      await composable.fetchCustomizedEventDuplicates();

      expect(spies.setMessage).toHaveBeenCalledOnce();
      expect(spies.setMessage).toHaveBeenCalledWith(expect.objectContaining({
        title: expect.any(String),
        description: expect.any(String),
      }));
    });

    it('should preserve existing state on error', async () => {
      // First, populate with data
      spies.getCustomizedEventDuplicates.mockResolvedValue(
        createMockDuplicatesResponse(['af-1'], ['mr-1'], ['ig-1']),
      );
      await composable.fetchCustomizedEventDuplicates();

      expect(get(composable.autoFixCount)).toBe(1);

      // Now fail the next fetch - state should remain unchanged
      spies.getCustomizedEventDuplicates.mockRejectedValue(new Error('fail'));
      await composable.fetchCustomizedEventDuplicates();

      expect(get(composable.autoFixGroupIds)).toEqual(['af-1']);
      expect(get(composable.manualReviewGroupIds)).toEqual(['mr-1']);
      expect(get(composable.ignoredGroupIds)).toEqual(['ig-1']);
    });
  });

  describe('computed counts', () => {
    it('should compute actionableCount as autoFix + manualReview', async () => {
      spies.getCustomizedEventDuplicates.mockResolvedValue(
        createMockDuplicatesResponse(['af-1', 'af-2'], ['mr-1', 'mr-2', 'mr-3'], ['ig-1']),
      );

      await composable.fetchCustomizedEventDuplicates();

      expect(get(composable.autoFixCount)).toBe(2);
      expect(get(composable.manualReviewCount)).toBe(3);
      expect(get(composable.actionableCount)).toBe(5);
    });

    it('should compute totalCount as actionable + ignored', async () => {
      spies.getCustomizedEventDuplicates.mockResolvedValue(
        createMockDuplicatesResponse(['af-1'], ['mr-1'], ['ig-1', 'ig-2']),
      );

      await composable.fetchCustomizedEventDuplicates();

      expect(get(composable.actionableCount)).toBe(2);
      expect(get(composable.ignoredCount)).toBe(2);
      expect(get(composable.totalCount)).toBe(4);
    });

    it('should have zero actionableCount when only ignored exist', async () => {
      spies.getCustomizedEventDuplicates.mockResolvedValue(
        createMockDuplicatesResponse([], [], ['ig-1', 'ig-2']),
      );

      await composable.fetchCustomizedEventDuplicates();

      expect(get(composable.actionableCount)).toBe(0);
      expect(get(composable.totalCount)).toBe(2);
    });
  });

  describe('fetchDuplicateEvents', () => {
    it('should return empty collection for empty groupIds', async () => {
      const result = await composable.fetchDuplicateEvents({
        groupIds: [],
        limit: 10,
        offset: 0,
      });

      expect(result.data).toEqual([]);
      expect(result.found).toBe(0);
      expect(result.total).toBe(0);
      expect(spies.fetchHistoryEvents).not.toHaveBeenCalled();
    });

    it('should return empty data for out-of-range offset', async () => {
      const result = await composable.fetchDuplicateEvents({
        groupIds: ['g-1', 'g-2'],
        limit: 10,
        offset: 10,
      });

      expect(result.data).toEqual([]);
      expect(result.found).toBe(2);
      expect(result.total).toBe(2);
      expect(spies.fetchHistoryEvents).not.toHaveBeenCalled();
    });

    it('should paginate group IDs and fetch events', async () => {
      const mockRow1 = createMockEventRow({ groupIdentifier: 'g-1', txRef: '0xTx1' });
      const mockRow2 = createMockEventRow({ groupIdentifier: 'g-2', txRef: '0xTx2' });

      spies.fetchHistoryEvents.mockResolvedValue({
        entries: [mockRow1, mockRow2],
        entriesFound: 2,
        entriesLimit: -1,
        entriesTotal: 2,
      });

      const result = await composable.fetchDuplicateEvents({
        groupIds: ['g-1', 'g-2', 'g-3'],
        limit: 2,
        offset: 0,
      });

      expect(spies.fetchHistoryEvents).toHaveBeenCalledWith(expect.objectContaining({
        groupIdentifiers: ['g-1', 'g-2'],
        limit: -1,
        offset: 0,
      }));

      expect(result.data).toHaveLength(2);
      expect(result.data[0].groupIdentifier).toBe('g-1');
      expect(result.data[0].txHash).toBe('0xTx1');
      expect(result.data[1].groupIdentifier).toBe('g-2');
      expect(result.data[1].txHash).toBe('0xTx2');
      expect(result.found).toBe(3);
      expect(result.total).toBe(3);
    });

    it('should map event fields to DuplicateRow correctly', async () => {
      const mockRow = createMockEventRow({
        groupIdentifier: 'g-1',
        location: 'optimism',
        locationLabel: '0xMyAddr',
        timestamp: 1700001234,
        txRef: '0xDeadBeef',
      });

      spies.fetchHistoryEvents.mockResolvedValue({
        entries: [mockRow],
        entriesFound: 1,
        entriesLimit: -1,
        entriesTotal: 1,
      });

      const result = await composable.fetchDuplicateEvents({
        groupIds: ['g-1'],
        limit: 10,
        offset: 0,
      });

      const row = result.data[0];
      expect(row.groupIdentifier).toBe('g-1');
      expect(row.location).toBe('optimism');
      expect(row.locationLabel).toBe('0xMyAddr');
      expect(row.timestamp).toBe(1700001234);
      expect(row.txHash).toBe('0xDeadBeef');
    });

    it('should handle events without locationLabel', async () => {
      const mockRow = createMockEventRow({
        groupIdentifier: 'g-1',
        locationLabel: null,
      });
      // Override to remove locationLabel
      (mockRow.entry as any).locationLabel = undefined;

      spies.fetchHistoryEvents.mockResolvedValue({
        entries: [mockRow],
        entriesFound: 1,
        entriesLimit: -1,
        entriesTotal: 1,
      });

      const result = await composable.fetchDuplicateEvents({
        groupIds: ['g-1'],
        limit: 10,
        offset: 0,
      });

      expect(result.data[0].locationLabel).toBeNull();
    });

    it('should handle events without txRef', async () => {
      const mockRow = createMockEventRow({ groupIdentifier: 'g-1' });
      // Remove txRef to test the fallback
      delete (mockRow.entry as any).txRef;

      spies.fetchHistoryEvents.mockResolvedValue({
        entries: [mockRow],
        entriesFound: 1,
        entriesLimit: -1,
        entriesTotal: 1,
      });

      const result = await composable.fetchDuplicateEvents({
        groupIds: ['g-1'],
        limit: 10,
        offset: 0,
      });

      expect(result.data[0].txHash).toBe('');
    });

    it('should handle events with null txRef', async () => {
      const mockRow = createMockEventRow({ groupIdentifier: 'g-1' });
      (mockRow.entry as any).txRef = null;

      spies.fetchHistoryEvents.mockResolvedValue({
        entries: [mockRow],
        entriesFound: 1,
        entriesLimit: -1,
        entriesTotal: 1,
      });

      const result = await composable.fetchDuplicateEvents({
        groupIds: ['g-1'],
        limit: 10,
        offset: 0,
      });

      expect(result.data[0].txHash).toBe('');
    });

    it('should handle array-style event rows', async () => {
      const mockEntry = createMockEventRow({ groupIdentifier: 'g-1', txRef: '0xArrayTx' });
      // Wrap in array to test getEventEntry array branch
      const arrayRow = [mockEntry] as unknown as HistoryEventCollectionRow;

      spies.fetchHistoryEvents.mockResolvedValue({
        entries: [arrayRow],
        entriesFound: 1,
        entriesLimit: -1,
        entriesTotal: 1,
      });

      const result = await composable.fetchDuplicateEvents({
        groupIds: ['g-1'],
        limit: 10,
        offset: 0,
      });

      expect(result.data).toHaveLength(1);
      expect(result.data[0].txHash).toBe('0xArrayTx');
    });

    it('should skip group IDs with no matching events', async () => {
      const mockRow = createMockEventRow({ groupIdentifier: 'g-1' });

      spies.fetchHistoryEvents.mockResolvedValue({
        entries: [mockRow],
        entriesFound: 1,
        entriesLimit: -1,
        entriesTotal: 1,
      });

      const result = await composable.fetchDuplicateEvents({
        groupIds: ['g-1', 'g-2'],
        limit: 10,
        offset: 0,
      });

      // g-2 has no matching events, so only g-1 appears
      expect(result.data).toHaveLength(1);
      expect(result.data[0].groupIdentifier).toBe('g-1');
    });

    it('should paginate with non-zero offset', async () => {
      const mockRow = createMockEventRow({ groupIdentifier: 'g-3', txRef: '0xPage2' });

      spies.fetchHistoryEvents.mockResolvedValue({
        entries: [mockRow],
        entriesFound: 1,
        entriesLimit: -1,
        entriesTotal: 1,
      });

      const result = await composable.fetchDuplicateEvents({
        groupIds: ['g-1', 'g-2', 'g-3', 'g-4'],
        limit: 2,
        offset: 2,
      });

      expect(spies.fetchHistoryEvents).toHaveBeenCalledWith(expect.objectContaining({
        groupIdentifiers: ['g-3', 'g-4'],
      }));
      expect(result.data).toHaveLength(1);
      expect(result.data[0].groupIdentifier).toBe('g-3');
      expect(result.found).toBe(4);
      expect(result.total).toBe(4);
    });
  });

  describe('fixDuplicates', () => {
    it('should call API with group identifiers', async () => {
      spies.fixCustomizedEventDuplicates.mockResolvedValue({
        removedEventIdentifiers: [1, 2],
        autoFixGroupIds: [],
      });
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      await composable.fixDuplicates(['g-1', 'g-2']);

      expect(spies.fixCustomizedEventDuplicates).toHaveBeenCalledWith(['g-1', 'g-2']);
    });

    it('should show success message when events are removed', async () => {
      spies.fixCustomizedEventDuplicates.mockResolvedValue({
        removedEventIdentifiers: [1, 2, 3],
        autoFixGroupIds: [],
      });
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      await composable.fixDuplicates(['g-1']);

      expect(spies.setMessage).toHaveBeenCalledWith(expect.objectContaining({
        success: true,
      }));
    });

    it('should not show success message when no events are removed', async () => {
      spies.fixCustomizedEventDuplicates.mockResolvedValue({
        removedEventIdentifiers: [],
        autoFixGroupIds: [],
      });
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      await composable.fixDuplicates(['g-1']);

      expect(spies.setMessage).not.toHaveBeenCalled();
    });

    it('should refresh list after fixing', async () => {
      spies.fixCustomizedEventDuplicates.mockResolvedValue({
        removedEventIdentifiers: [],
        autoFixGroupIds: [],
      });
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      await composable.fixDuplicates(['g-1']);

      expect(spies.getCustomizedEventDuplicates).toHaveBeenCalledOnce();
    });

    it('should return success status', async () => {
      spies.fixCustomizedEventDuplicates.mockResolvedValue({
        removedEventIdentifiers: [],
        autoFixGroupIds: [],
      });
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      const result = await composable.fixDuplicates(['g-1']);

      expect(result).toEqual({ success: true });
    });

    it('should set fixLoading during operation and reset after', async () => {
      const loadingDuringCall: boolean[] = [];
      spies.fixCustomizedEventDuplicates.mockImplementation(async () => {
        loadingDuringCall.push(get(composable.fixLoading));
        return { removedEventIdentifiers: [], autoFixGroupIds: [] };
      });
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      await composable.fixDuplicates(['g-1']);

      expect(loadingDuringCall[0]).toBe(true);
      expect(get(composable.fixLoading)).toBe(false);
    });

    it('should handle errors and return failure status', async () => {
      spies.fixCustomizedEventDuplicates.mockRejectedValue(new Error('Fix failed'));

      const result = await composable.fixDuplicates(['g-1']);

      expect(result).toEqual({ message: 'Fix failed', success: false });
      expect(spies.setMessage).toHaveBeenCalledWith(expect.objectContaining({
        title: expect.any(String),
        description: expect.any(String),
      }));
    });

    it('should reset fixLoading on error', async () => {
      spies.fixCustomizedEventDuplicates.mockRejectedValue(new Error('Fix failed'));

      await composable.fixDuplicates(['g-1']);

      expect(get(composable.fixLoading)).toBe(false);
    });

    it('should call API without arguments when no group identifiers provided', async () => {
      spies.fixCustomizedEventDuplicates.mockResolvedValue({
        removedEventIdentifiers: [1],
        autoFixGroupIds: [],
      });
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      const result = await composable.fixDuplicates();

      expect(spies.fixCustomizedEventDuplicates).toHaveBeenCalledWith(undefined);
      expect(result).toEqual({ success: true });
    });
  });

  describe('ignoreDuplicates', () => {
    it('should call API with group identifiers', async () => {
      spies.ignoreCustomizedEventDuplicates.mockResolvedValue(['g-1']);
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      await composable.ignoreDuplicates(['g-1']);

      expect(spies.ignoreCustomizedEventDuplicates).toHaveBeenCalledWith(['g-1']);
    });

    it('should refresh list after ignoring', async () => {
      spies.ignoreCustomizedEventDuplicates.mockResolvedValue(['g-1']);
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      await composable.ignoreDuplicates(['g-1']);

      expect(spies.getCustomizedEventDuplicates).toHaveBeenCalledOnce();
    });

    it('should return success status', async () => {
      spies.ignoreCustomizedEventDuplicates.mockResolvedValue(['g-1']);
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      const result = await composable.ignoreDuplicates(['g-1']);

      expect(result).toEqual({ success: true });
    });

    it('should set ignoreLoading during operation and reset after', async () => {
      const loadingDuringCall: boolean[] = [];
      spies.ignoreCustomizedEventDuplicates.mockImplementation(async () => {
        loadingDuringCall.push(get(composable.ignoreLoading));
        return ['g-1'];
      });
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      await composable.ignoreDuplicates(['g-1']);

      expect(loadingDuringCall[0]).toBe(true);
      expect(get(composable.ignoreLoading)).toBe(false);
    });

    it('should handle errors and return failure status', async () => {
      spies.ignoreCustomizedEventDuplicates.mockRejectedValue(new Error('Ignore failed'));

      const result = await composable.ignoreDuplicates(['g-1']);

      expect(result).toEqual({ message: 'Ignore failed', success: false });
      expect(spies.setMessage).toHaveBeenCalledOnce();
    });

    it('should reset ignoreLoading on error', async () => {
      spies.ignoreCustomizedEventDuplicates.mockRejectedValue(new Error('Ignore failed'));

      await composable.ignoreDuplicates(['g-1']);

      expect(get(composable.ignoreLoading)).toBe(false);
    });
  });

  describe('unignoreDuplicates', () => {
    it('should call API with group identifiers', async () => {
      spies.unignoreCustomizedEventDuplicates.mockResolvedValue(['g-1']);
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      await composable.unignoreDuplicates(['g-1']);

      expect(spies.unignoreCustomizedEventDuplicates).toHaveBeenCalledWith(['g-1']);
    });

    it('should refresh list after unignoring', async () => {
      spies.unignoreCustomizedEventDuplicates.mockResolvedValue(['g-1']);
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      await composable.unignoreDuplicates(['g-1']);

      expect(spies.getCustomizedEventDuplicates).toHaveBeenCalledOnce();
    });

    it('should return success status', async () => {
      spies.unignoreCustomizedEventDuplicates.mockResolvedValue(['g-1']);
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      const result = await composable.unignoreDuplicates(['g-1']);

      expect(result).toEqual({ success: true });
    });

    it('should set ignoreLoading during operation and reset after', async () => {
      const loadingDuringCall: boolean[] = [];
      spies.unignoreCustomizedEventDuplicates.mockImplementation(async () => {
        loadingDuringCall.push(get(composable.ignoreLoading));
        return ['g-1'];
      });
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      await composable.unignoreDuplicates(['g-1']);

      expect(loadingDuringCall[0]).toBe(true);
      expect(get(composable.ignoreLoading)).toBe(false);
    });

    it('should handle errors and return failure status', async () => {
      spies.unignoreCustomizedEventDuplicates.mockRejectedValue(new Error('Unignore failed'));

      const result = await composable.unignoreDuplicates(['g-1']);

      expect(result).toEqual({ message: 'Unignore failed', success: false });
      expect(spies.setMessage).toHaveBeenCalledOnce();
    });

    it('should reset ignoreLoading on error', async () => {
      spies.unignoreCustomizedEventDuplicates.mockRejectedValue(new Error('Unignore failed'));

      await composable.unignoreDuplicates(['g-1']);

      expect(get(composable.ignoreLoading)).toBe(false);
    });
  });

  describe('confirmAndFixDuplicate', () => {
    it('should show confirm dialog for single item', () => {
      composable.confirmAndFixDuplicate(['g-1']);

      expect(spies.showConfirm).toHaveBeenCalledOnce();
      const [message] = spies.showConfirm.mock.calls[0];
      expect(message).toMatchObject({
        title: expect.any(String),
        message: expect.any(String),
        primaryAction: expect.any(String),
      });
    });

    it('should show confirm dialog for multiple items', () => {
      composable.confirmAndFixDuplicate(['g-1', 'g-2', 'g-3']);

      expect(spies.showConfirm).toHaveBeenCalledOnce();
      const [message] = spies.showConfirm.mock.calls[0];
      expect(message).toMatchObject({
        title: expect.any(String),
        message: expect.any(String),
        primaryAction: expect.any(String),
      });
    });

    it('callback should call fixDuplicates with group identifiers', async () => {
      spies.fixCustomizedEventDuplicates.mockResolvedValue({
        removedEventIdentifiers: [1],
        autoFixGroupIds: [],
      });
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      composable.confirmAndFixDuplicate(['g-1', 'g-2']);
      await extractAndCallConfirmCallback();

      expect(spies.fixCustomizedEventDuplicates).toHaveBeenCalledWith(['g-1', 'g-2']);
    });

    it('callback should call onSuccess when fix succeeds', async () => {
      spies.fixCustomizedEventDuplicates.mockResolvedValue({
        removedEventIdentifiers: [1],
        autoFixGroupIds: [],
      });
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      const onSuccess = vi.fn();
      composable.confirmAndFixDuplicate(['g-1'], onSuccess);
      await extractAndCallConfirmCallback();

      expect(onSuccess).toHaveBeenCalledOnce();
    });

    it('callback should not call onSuccess when fix fails', async () => {
      spies.fixCustomizedEventDuplicates.mockRejectedValue(new Error('Fix failed'));

      const onSuccess = vi.fn();
      composable.confirmAndFixDuplicate(['g-1'], onSuccess);
      await extractAndCallConfirmCallback();

      expect(onSuccess).not.toHaveBeenCalled();
    });

    it('should use different messages for single vs bulk', () => {
      composable.confirmAndFixDuplicate(['g-1']);
      const [singleMessage] = spies.showConfirm.mock.calls[0];

      vi.clearAllMocks();

      composable.confirmAndFixDuplicate(['g-1', 'g-2']);
      const [bulkMessage] = spies.showConfirm.mock.calls[0];

      expect(singleMessage.title).not.toBe(bulkMessage.title);
      expect(singleMessage.message).not.toBe(bulkMessage.message);
    });

    it('callback should work without onSuccess', async () => {
      spies.fixCustomizedEventDuplicates.mockResolvedValue({
        removedEventIdentifiers: [1],
        autoFixGroupIds: [],
      });
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      composable.confirmAndFixDuplicate(['g-1']);
      await extractAndCallConfirmCallback();

      expect(spies.fixCustomizedEventDuplicates).toHaveBeenCalledWith(['g-1']);
    });
  });

  describe('confirmAndMarkNonDuplicated', () => {
    it('should show confirm dialog for single item', () => {
      composable.confirmAndMarkNonDuplicated(['g-1']);

      expect(spies.showConfirm).toHaveBeenCalledOnce();
      const [message] = spies.showConfirm.mock.calls[0];
      expect(message).toMatchObject({
        title: expect.any(String),
        message: expect.any(String),
        primaryAction: expect.any(String),
      });
    });

    it('should show confirm dialog for multiple items', () => {
      composable.confirmAndMarkNonDuplicated(['g-1', 'g-2']);

      expect(spies.showConfirm).toHaveBeenCalledOnce();
      const [message] = spies.showConfirm.mock.calls[0];
      expect(message).toMatchObject({
        title: expect.any(String),
        message: expect.any(String),
        primaryAction: expect.any(String),
      });
    });

    it('callback should call ignoreDuplicates with group identifiers', async () => {
      spies.ignoreCustomizedEventDuplicates.mockResolvedValue(['g-1']);
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      composable.confirmAndMarkNonDuplicated(['g-1']);
      await extractAndCallConfirmCallback();

      expect(spies.ignoreCustomizedEventDuplicates).toHaveBeenCalledWith(['g-1']);
    });

    it('callback should call onSuccess when ignore succeeds', async () => {
      spies.ignoreCustomizedEventDuplicates.mockResolvedValue(['g-1']);
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      const onSuccess = vi.fn();
      composable.confirmAndMarkNonDuplicated(['g-1'], onSuccess);
      await extractAndCallConfirmCallback();

      expect(onSuccess).toHaveBeenCalledOnce();
    });

    it('callback should not call onSuccess when ignore fails', async () => {
      spies.ignoreCustomizedEventDuplicates.mockRejectedValue(new Error('Ignore failed'));

      const onSuccess = vi.fn();
      composable.confirmAndMarkNonDuplicated(['g-1'], onSuccess);
      await extractAndCallConfirmCallback();

      expect(onSuccess).not.toHaveBeenCalled();
    });

    it('should use different messages for single vs bulk', () => {
      composable.confirmAndMarkNonDuplicated(['g-1']);
      const [singleMessage] = spies.showConfirm.mock.calls[0];

      vi.clearAllMocks();

      composable.confirmAndMarkNonDuplicated(['g-1', 'g-2']);
      const [bulkMessage] = spies.showConfirm.mock.calls[0];

      expect(singleMessage.title).not.toBe(bulkMessage.title);
      expect(singleMessage.message).not.toBe(bulkMessage.message);
    });

    it('callback should work without onSuccess', async () => {
      spies.ignoreCustomizedEventDuplicates.mockResolvedValue(['g-1']);
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      composable.confirmAndMarkNonDuplicated(['g-1']);
      await extractAndCallConfirmCallback();

      expect(spies.ignoreCustomizedEventDuplicates).toHaveBeenCalledWith(['g-1']);
    });
  });

  describe('confirmAndRestore', () => {
    it('should show confirm dialog for single item', () => {
      composable.confirmAndRestore(['g-1']);

      expect(spies.showConfirm).toHaveBeenCalledOnce();
      const [message] = spies.showConfirm.mock.calls[0];
      expect(message).toMatchObject({
        title: expect.any(String),
        message: expect.any(String),
        primaryAction: expect.any(String),
      });
    });

    it('should show confirm dialog for multiple items', () => {
      composable.confirmAndRestore(['g-1', 'g-2']);

      expect(spies.showConfirm).toHaveBeenCalledOnce();
      const [message] = spies.showConfirm.mock.calls[0];
      expect(message).toMatchObject({
        title: expect.any(String),
        message: expect.any(String),
        primaryAction: expect.any(String),
      });
    });

    it('callback should call unignoreDuplicates with group identifiers', async () => {
      spies.unignoreCustomizedEventDuplicates.mockResolvedValue(['g-1']);
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      composable.confirmAndRestore(['g-1']);
      await extractAndCallConfirmCallback();

      expect(spies.unignoreCustomizedEventDuplicates).toHaveBeenCalledWith(['g-1']);
    });

    it('callback should call onSuccess when unignore succeeds', async () => {
      spies.unignoreCustomizedEventDuplicates.mockResolvedValue(['g-1']);
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      const onSuccess = vi.fn();
      composable.confirmAndRestore(['g-1'], onSuccess);
      await extractAndCallConfirmCallback();

      expect(onSuccess).toHaveBeenCalledOnce();
    });

    it('callback should not call onSuccess when unignore fails', async () => {
      spies.unignoreCustomizedEventDuplicates.mockRejectedValue(new Error('Unignore failed'));

      const onSuccess = vi.fn();
      composable.confirmAndRestore(['g-1'], onSuccess);
      await extractAndCallConfirmCallback();

      expect(onSuccess).not.toHaveBeenCalled();
    });

    it('should use different messages for single vs bulk', () => {
      composable.confirmAndRestore(['g-1']);
      const [singleMessage] = spies.showConfirm.mock.calls[0];

      vi.clearAllMocks();

      composable.confirmAndRestore(['g-1', 'g-2']);
      const [bulkMessage] = spies.showConfirm.mock.calls[0];

      expect(singleMessage.title).not.toBe(bulkMessage.title);
      expect(singleMessage.message).not.toBe(bulkMessage.message);
    });

    it('callback should work without onSuccess', async () => {
      spies.unignoreCustomizedEventDuplicates.mockResolvedValue(['g-1']);
      spies.getCustomizedEventDuplicates.mockResolvedValue(createMockDuplicatesResponse());

      composable.confirmAndRestore(['g-1']);
      await extractAndCallConfirmCallback();

      expect(spies.unignoreCustomizedEventDuplicates).toHaveBeenCalledWith(['g-1']);
    });
  });
});
