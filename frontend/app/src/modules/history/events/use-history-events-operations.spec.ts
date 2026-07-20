import type { PullEventPayload } from '@/modules/history/events/event-payloads';
import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';
import type { HistoryEventsTableEmitFn } from '@/modules/history/events/types';
import { HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryEventsOperations } from './use-history-events-operations';

const { spies } = vi.hoisted(() => ({
  spies: {
    show: vi.fn(),
    notifyError: vi.fn(),
    getChain: vi.fn((location: string) => location),
    deleteTransactions: vi.fn(),
    unlinkAssetMovement: vi.fn(),
    refreshUnmatchedAssetMovements: vi.fn(),
    deleteHistoryEvent: vi.fn(),
    ignoreSingle: vi.fn(),
    toggle: vi.fn(),
    getGroupEvents: vi.fn(() => [] as HistoryEventEntry[]),
    isAssetMovementEvent: vi.fn(() => false),
    isCustomizedEvent: vi.fn(() => false),
  },
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): object => ({ show: spies.show }),
}));
vi.mock('@/modules/core/notifications/use-notifications', async () => {
  const actual = await vi.importActual<typeof import('@/modules/core/notifications/use-notifications')>('@/modules/core/notifications/use-notifications');
  return { ...actual, useNotifications: (): object => ({ notifyError: spies.notifyError }) };
});
vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({ getChain: spies.getChain }),
}));
vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: (): object => ({ deleteTransactions: spies.deleteTransactions }),
}));
vi.mock('@/modules/history/api/events/use-asset-movement-matching-api', () => ({
  useAssetMovementMatchingApi: (): object => ({ unlinkAssetMovement: spies.unlinkAssetMovement }),
}));
vi.mock('@/modules/history/events/use-unmatched-asset-movements', () => ({
  useUnmatchedAssetMovements: (): object => ({ refreshUnmatchedAssetMovements: spies.refreshUnmatchedAssetMovements }),
}));
vi.mock('@/modules/history/events/use-history-events', () => ({
  useHistoryEvents: (): object => ({ deleteHistoryEvent: spies.deleteHistoryEvent }),
}));
vi.mock('@/modules/history/use-ignore', () => ({
  useIgnore: (): object => ({ ignoreSingle: spies.ignoreSingle, toggle: spies.toggle }),
}));
vi.mock('@/modules/history/events/use-complete-events', () => ({
  useCompleteEvents: (): object => ({ getGroupEvents: spies.getGroupEvents }),
}));
vi.mock('@/modules/history/event-utils', async () => {
  const actual = await vi.importActual<typeof import('@/modules/history/event-utils')>('@/modules/history/event-utils');
  return { ...actual, isAssetMovementEvent: spies.isAssetMovementEvent, isCustomizedEvent: spies.isCustomizedEvent };
});

const emit = vi.fn() as unknown as HistoryEventsTableEmitFn;

function setup(flattened: HistoryEventEntry[] = []): ReturnType<typeof useHistoryEventsOperations> {
  return useHistoryEventsOperations({
    completeEventsMapped: computed<Record<string, HistoryEventRow[]>>(() => ({})),
    flattenedEvents: computed<HistoryEventEntry[]>(() => flattened),
  }, emit);
}

const evmPayload: PullEventPayload = { data: { location: 'ethereum', txRef: '0x1' }, type: HistoryEventEntryType.EVM_EVENT };
const blockPayload: PullEventPayload = { data: [123], type: HistoryEventEntryType.ETH_BLOCK_EVENT };

describe('useHistoryEventsOperations', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.clearAllMocks();
    spies.getChain.mockImplementation((location: string) => location);
    spies.getGroupEvents.mockReturnValue([]);
    spies.isAssetMovementEvent.mockReturnValue(false);
    spies.isCustomizedEvent.mockReturnValue(false);
  });

  it('should dim ignored events via the item class', () => {
    const ops = setup();
    expect(ops.getItemClass(createMock<HistoryEventEntry>({ ignoredInAccounting: true }))).toBe('opacity-50');
    expect(ops.getItemClass(createMock<HistoryEventEntry>({ ignoredInAccounting: false }))).toBe('');
  });

  it('should suggest the next sequence id from the group max', () => {
    const flattened = [
      createMock<HistoryEventEntry>({ groupIdentifier: 'g1', hidden: false, sequenceIndex: 2 }),
      createMock<HistoryEventEntry>({ groupIdentifier: 'g1', hidden: false, sequenceIndex: 5 }),
      createMock<HistoryEventEntry>({ groupIdentifier: 'g1', hidden: true, sequenceIndex: 9 }), // hidden ignored
      createMock<HistoryEventEntry>({ groupIdentifier: 'other', hidden: false, sequenceIndex: 20 }),
    ];
    const ops = setup(flattened);
    expect(ops.suggestNextSequenceId(createMock<HistoryEventEntry>({ groupIdentifier: 'g1', sequenceIndex: 0 }))).toBe('6');
  });

  it('should fall back to group sequence + 1 when nothing is flattened', () => {
    const ops = setup([]);
    expect(ops.suggestNextSequenceId(createMock<HistoryEventEntry>({ groupIdentifier: 'g1', sequenceIndex: 7 }))).toBe('8');
  });

  it('should emit a block-event refresh when redecoding a block payload', () => {
    setup().redecode(blockPayload, 'g1');
    expect(emit).toHaveBeenCalledWith('refresh:block-event', { blockNumbers: [123] });
  });

  it('should open the confirmation dialog when the group has custom events', () => {
    spies.getGroupEvents.mockReturnValue([createMock<HistoryEventEntry>({})]);
    spies.isCustomizedEvent.mockReturnValue(true);
    const ops = setup();
    ops.redecode(evmPayload, 'g1');
    expect(get(ops.hasCustomEvents)).toBe(true);
    expect(get(ops.modelShowRedecodeConfirmation)).toBe(true);
    expect(get(ops.redecodePayload)).toEqual(evmPayload);
    expect(emit).not.toHaveBeenCalledWith('refresh', expect.anything());
  });

  it('should redecode directly when there are no custom events', () => {
    spies.getGroupEvents.mockReturnValue([createMock<HistoryEventEntry>({})]);
    setup().redecode(evmPayload, 'g1');
    expect(emit).toHaveBeenCalledWith('refresh', {
      deleteCustom: false,
      linkedMovement: undefined,
      transactions: [evmPayload.data],
    });
  });

  it('should show indexer options for EVM redecode-with-options', () => {
    spies.getGroupEvents.mockReturnValue([createMock<HistoryEventEntry>({})]);
    const ops = setup();
    ops.redecodeWithOptions(evmPayload, 'g1');
    expect(get(ops.showIndexerOptions)).toBe(true);
    expect(get(ops.modelShowRedecodeConfirmation)).toBe(true);
    expect(get(ops.redecodePayload)).toEqual(evmPayload);
  });

  it('should emit refresh and reset payload on confirm-redecode', () => {
    const ops = setup();
    ops.confirmRedecode({ deleteCustom: true, payload: evmPayload });
    expect(emit).toHaveBeenCalledWith('refresh', expect.objectContaining({
      deleteCustom: true,
      transactions: [evmPayload.data],
    }));
    expect(get(ops.redecodePayload)).toBeUndefined();
  });

  it('should delete events through the confirmation callback', async () => {
    spies.deleteHistoryEvent.mockResolvedValue({ success: true });
    setup().confirmDelete({ ids: [1, 2], type: 'delete' });
    expect(spies.show).toHaveBeenCalledOnce();
    await spies.show.mock.calls[0][1]();
    expect(spies.deleteHistoryEvent).toHaveBeenCalledWith([1, 2]);
    expect(emit).toHaveBeenCalledWith('refresh');
  });

  it('should ignore an event through the confirmation callback', async () => {
    const event = createMock<HistoryEventEntry>({ identifier: 1 });
    setup().confirmDelete({ event, type: 'ignore' });
    await spies.show.mock.calls[0][1]();
    expect(spies.ignoreSingle).toHaveBeenCalledWith(event, true);
    expect(spies.deleteHistoryEvent).not.toHaveBeenCalled();
  });

  it('should delete a transaction and its events, notifying on error', async () => {
    setup().confirmTxAndEventsDelete({ location: 'ethereum', txRef: '0x1' });
    await spies.show.mock.calls[0][1]();
    expect(spies.deleteTransactions).toHaveBeenCalledWith('ethereum', '0x1');
    expect(emit).toHaveBeenCalledWith('refresh');

    spies.deleteTransactions.mockRejectedValueOnce(new Error('boom'));
    setup().confirmTxAndEventsDelete({ location: 'ethereum', txRef: '0x2' });
    await spies.show.mock.calls[1][1]();
    expect(spies.notifyError).toHaveBeenCalledOnce();
  });

  it('should unlink an asset movement through the confirmation callback', async () => {
    setup().confirmUnlink({ identifier: 9 });
    await spies.show.mock.calls[0][1]();
    expect(spies.unlinkAssetMovement).toHaveBeenCalledWith(9);
    expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
    expect(emit).toHaveBeenCalledWith('refresh');
  });
});
