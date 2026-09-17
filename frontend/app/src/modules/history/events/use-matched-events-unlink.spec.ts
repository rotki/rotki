import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';
import type { HistoryEventsTableEmitFn } from '@/modules/history/events/types';
import { createMock } from '@test/utils/create-mock';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useMatchedEventsUnlink } from './use-matched-events-unlink';

const { spies } = vi.hoisted(() => ({
  spies: {
    busEmit: vi.fn(),
    getGroupEvents: vi.fn((): HistoryEventEntry[] => []),
    isAssetMovementEvent: vi.fn(() => false),
    notifyError: vi.fn(),
    refreshUnmatchedAssetMovements: vi.fn(),
    refreshUnmatchedBridgeTransactions: vi.fn(),
    show: vi.fn(),
    unlinkAssetMovement: vi.fn(),
    unlinkBridgeTransaction: vi.fn(),
  },
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): object => ({ show: spies.show }),
}));
vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): object => ({ notifyError: spies.notifyError }),
}));
vi.mock('@/modules/history/api/events/use-asset-movement-matching-api', () => ({
  useAssetMovementMatchingApi: (): object => ({ unlinkAssetMovement: spies.unlinkAssetMovement }),
}));
vi.mock('@/modules/history/api/events/use-bridge-matching-api', () => ({
  useBridgeMatchingApi: (): object => ({ unlinkBridgeTransaction: spies.unlinkBridgeTransaction }),
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
  isAssetMovementEvent: spies.isAssetMovementEvent,
}));
vi.mock('@/modules/task-center/events/task-center-bus', () => ({
  taskCenterBus: { emit: spies.busEmit },
}));

const emit: HistoryEventsTableEmitFn = vi.fn();

function setup(): ReturnType<typeof useMatchedEventsUnlink> {
  return useMatchedEventsUnlink(computed<Record<string, HistoryEventRow[]>>(() => ({})), emit);
}

async function confirm(): Promise<void> {
  await spies.show.mock.calls.at(-1)?.[1]();
}

describe('useMatchedEventsUnlink', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should unlink an asset movement and refresh the unmatched movements', async () => {
    setup().confirmUnlink({ identifier: 9, type: 'asset-movement' });
    expect(spies.show.mock.calls[0][0].message).toBe('transactions.events.confirmation.unlink.message');
    await confirm();

    expect(spies.unlinkAssetMovement).toHaveBeenCalledWith(9);
    expect(spies.refreshUnmatchedAssetMovements).toHaveBeenCalledOnce();
    expect(spies.unlinkBridgeTransaction).not.toHaveBeenCalled();
    expect(emit).toHaveBeenCalledWith('refresh');
  });

  it('should unlink a bridge transfer through the bridge endpoint', async () => {
    setup().confirmUnlink({ identifier: 21, type: 'bridge' });
    expect(spies.show.mock.calls[0][0].message).toBe('transactions.events.confirmation.unlink.bridge_message');
    await confirm();

    expect(spies.unlinkBridgeTransaction).toHaveBeenCalledWith(21);
    expect(spies.refreshUnmatchedBridgeTransactions).toHaveBeenCalledOnce();
    expect(spies.unlinkAssetMovement).not.toHaveBeenCalled();
    expect(spies.refreshUnmatchedAssetMovements).not.toHaveBeenCalled();
    expect(emit).toHaveBeenCalledWith('refresh');
    expect(spies.busEmit).toHaveBeenCalledOnce();
  });

  it('should report a failed bridge unlink without refreshing', async () => {
    spies.unlinkBridgeTransaction.mockRejectedValueOnce(new Error('boom'));
    setup().confirmUnlink({ identifier: 21, type: 'bridge' });
    await confirm();

    expect(spies.notifyError).toHaveBeenCalledWith('transactions.events.unlink_bridge_error', 'boom');
    expect(emit).not.toHaveBeenCalled();
    expect(spies.busEmit).not.toHaveBeenCalled();
  });

  it('should unlink the matched movement of a group from its header', async () => {
    const fee = createMock<HistoryEventEntry>({ actualGroupIdentifier: 'tx', eventSubtype: 'fee', identifier: 4 });
    const movement = createMock<HistoryEventEntry>({ actualGroupIdentifier: 'tx', eventSubtype: 'remove asset', identifier: 5 });
    spies.getGroupEvents.mockReturnValueOnce([fee, movement]);
    spies.isAssetMovementEvent.mockReturnValueOnce(true).mockReturnValueOnce(true);

    setup().unlinkGroup('group-1');
    await confirm();

    expect(spies.unlinkAssetMovement).toHaveBeenCalledWith(5);
  });
});
