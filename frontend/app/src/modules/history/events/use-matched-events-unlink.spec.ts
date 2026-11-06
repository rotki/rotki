import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';
import type { HistoryEventsTableEmitFn } from '@/modules/history/events/types';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryEventsActionFailure } from './use-history-events-action-failure';
import { useMatchedEventsUnlink } from './use-matched-events-unlink';

const { spies } = vi.hoisted(() => ({
  spies: {
    busEmit: vi.fn(),
    getGroupEvents: vi.fn((): HistoryEventEntry[] => []),
    matchBridgeTransactions: vi.fn(),
    getMatchedMovementIgnoreIds: vi.fn((): number[] => []),
    isAssetMovementEvent: vi.fn(() => false),
    matchAssetMovements: vi.fn(),
    refreshUnmatchedAssetMovements: vi.fn(),
    refreshUnmatchedBridgeTransactions: vi.fn(),
    unlinkAssetMovement: vi.fn(),
    unlinkBridgeTransaction: vi.fn(),
  },
}));

vi.mock('@/modules/history/api/events/use-asset-movement-matching-api', () => ({
  useAssetMovementMatchingApi: (): object => ({
    matchAssetMovements: spies.matchAssetMovements,
    unlinkAssetMovement: spies.unlinkAssetMovement,
  }),
}));
vi.mock('@/modules/history/api/events/use-bridge-matching-api', () => ({
  useBridgeMatchingApi: (): object => ({
    matchBridgeTransactions: spies.matchBridgeTransactions,
    unlinkBridgeTransaction: spies.unlinkBridgeTransaction,
  }),
}));
vi.mock('@/modules/history/events/use-unmatched-asset-movements', () => ({
  useUnmatchedAssetMovements: (): object => ({ refreshUnmatchedAssetMovements: spies.refreshUnmatchedAssetMovements }),
}));
vi.mock('@/modules/history/events/use-unmatched-bridge-transactions', () => ({
  useUnmatchedBridgeTransactions: (): object => ({ refreshUnmatchedBridgeTransactions: spies.refreshUnmatchedBridgeTransactions }),
}));
vi.mock('@/modules/history/events/use-complete-events', () => ({
  useCompleteEvents: (): object => ({ getGroupEvents: spies.getGroupEvents }),
}));
vi.mock('@/modules/history/event-utils', () => ({
  getMatchedMovementIgnoreIds: spies.getMatchedMovementIgnoreIds,
  isAssetMovementEvent: spies.isAssetMovementEvent,
}));
vi.mock('@/modules/task-center/events/task-center-bus', () => ({
  taskCenterBus: { emit: spies.busEmit },
}));

const emit: HistoryEventsTableEmitFn = vi.fn();

function setup(): ReturnType<typeof useMatchedEventsUnlink> {
  return useMatchedEventsUnlink(computed<Record<string, HistoryEventRow[]>>(() => ({})), emit);
}

const { failure: actionFailure, clear: clearActionFailure, report: reportActionFailure } = useHistoryEventsActionFailure();

describe('useMatchedEventsUnlink', () => {
  beforeEach(() => {
    clearActionFailure();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should unlink an asset movement and ignore its movement legs', async () => {
    await setup().unlink({ identifier: 9, ignoredIdentifiers: [9], type: 'asset-movement' });

    expect(spies.unlinkAssetMovement).toHaveBeenCalledWith(9);
    // same durability as a bridge unlink: the matcher would otherwise relink it on its next run
    expect(spies.matchAssetMovements.mock.calls).toStrictEqual([[9]]);
    expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
    expect(spies.unlinkBridgeTransaction).not.toHaveBeenCalled();
    expect(emit).toHaveBeenCalledWith('refresh');
  });

  it('should not ignore any movement leg when the unlink itself fails', async () => {
    spies.unlinkAssetMovement.mockRejectedValueOnce(new Error('boom'));
    await setup().unlink({ identifier: 9, ignoredIdentifiers: [9, 10], type: 'asset-movement' });

    expect(spies.matchAssetMovements).not.toHaveBeenCalled();
    expect(get(actionFailure)).toEqual({ failure: new Error('boom'), title: 'transactions.events.unlink_error' });
  });

  it('should unlink a bridge transfer and ignore both legs', async () => {
    await setup().unlink({ hasSynthetic: false, identifier: 21, ignoredIdentifiers: [21, 22], type: 'bridge' });

    expect(spies.unlinkBridgeTransaction).toHaveBeenCalledWith(21);
    // ignoring is matching with no counterpart, and keeps the automatic matcher off both legs
    expect(spies.matchBridgeTransactions.mock.calls).toStrictEqual([[21], [22]]);
    expect(spies.refreshUnmatchedBridgeTransactions).toHaveBeenCalledOnce();
    expect(spies.unlinkAssetMovement).not.toHaveBeenCalled();
    expect(spies.refreshUnmatchedAssetMovements).not.toHaveBeenCalled();
    expect(emit).toHaveBeenCalledWith('refresh');
    expect(spies.busEmit).toHaveBeenCalledOnce();
  });

  it('should ignore only the real leg when the synthetic counterpart is deleted', async () => {
    await setup().unlink({ hasSynthetic: true, identifier: 21, ignoredIdentifiers: [21], type: 'bridge' });

    expect(spies.matchBridgeTransactions.mock.calls).toStrictEqual([[21]]);
  });

  it('should not ignore any leg when the unlink itself fails', async () => {
    spies.unlinkBridgeTransaction.mockRejectedValueOnce(new Error('boom'));
    await setup().unlink({ hasSynthetic: false, identifier: 21, ignoredIdentifiers: [21, 22], type: 'bridge' });

    expect(spies.matchBridgeTransactions).not.toHaveBeenCalled();
    expect(get(actionFailure)).toEqual({ failure: new Error('boom'), title: 'transactions.events.unlink_bridge_error' });
  });

  it('should drop the last failure when the next unlink starts', async () => {
    reportActionFailure('transactions.events.unlink_error', 'boom');

    await setup().unlink({ identifier: 9, ignoredIdentifiers: [9], type: 'asset-movement' });

    expect(get(actionFailure)).toBeUndefined();
  });

  it('should report a failed bridge unlink without refreshing', async () => {
    spies.unlinkBridgeTransaction.mockRejectedValueOnce(new Error('boom'));
    await setup().unlink({ hasSynthetic: false, identifier: 21, ignoredIdentifiers: [21], type: 'bridge' });

    expect(get(actionFailure)).toEqual({ failure: new Error('boom'), title: 'transactions.events.unlink_bridge_error' });
    expect(emit).not.toHaveBeenCalled();
    expect(spies.busEmit).not.toHaveBeenCalled();
  });

  it('should unlink the matched movement of a group from its header', async () => {
    const fee = createMock<HistoryEventEntry>({ actualGroupIdentifier: 'tx', eventSubtype: 'fee', identifier: 4 });
    const movement = createMock<HistoryEventEntry>({ actualGroupIdentifier: 'tx', eventSubtype: 'remove asset', identifier: 5 });
    spies.getGroupEvents.mockReturnValueOnce([fee, movement]);
    spies.isAssetMovementEvent.mockReturnValueOnce(true).mockReturnValueOnce(true);

    await setup().unlinkGroup('group-1');

    expect(spies.unlinkAssetMovement).toHaveBeenCalledWith(5);
  });
});
