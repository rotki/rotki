import type { Result } from 'plainfp/result';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { neverSettles } from '@test/utils/never-settles';
import { beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * Imports fresh copies of the shared composable and everything it reads. `createSharedComposable`
 * keeps the stores it resolved on first use, so a new pinia per test also needs a new composable.
 */
async function setup(): Promise<{
  status: ReturnType<typeof import('./use-history-events-status').useHistoryEventsStatus>;
  orchestrator: ReturnType<typeof import('@/modules/task-center/use-task-orchestrator').useTaskOrchestrator>;
  txStore: ReturnType<typeof import('@/modules/history/use-tx-query-status-store').useTxQueryStatusStore>;
  eventsStore: ReturnType<typeof import('@/modules/history/use-events-query-status-store').useEventsQueryStatusStore>;
  types: typeof import('@/modules/task-center/core/types');
}> {
  vi.resetModules();
  const [statusModule, orchestratorModule, txModule, eventsModule, types] = await Promise.all([
    import('./use-history-events-status'),
    import('@/modules/task-center/use-task-orchestrator'),
    import('@/modules/history/use-tx-query-status-store'),
    import('@/modules/history/use-events-query-status-store'),
    import('@/modules/task-center/core/types'),
  ]);

  const orchestrator = orchestratorModule.useTaskOrchestrator();
  orchestrator.reset();

  return {
    eventsStore: eventsModule.useEventsQueryStatusStore(),
    orchestrator,
    status: statusModule.useHistoryEventsStatus(),
    txStore: txModule.useTxQueryStatusStore(),
    types,
  };
}

describe('useHistoryEventsStatus', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  describe('shouldFetchEventsRegularly', () => {
    it('should be off when the stores still list unfinished work but the ledger is idle', async () => {
      const { eventsStore, status, txStore } = await setup();

      txStore.initializeQueryStatus([{ address: '0x123', chain: 'eth', subtype: 'evm' }]);
      eventsStore.initializeQueryStatus([{ location: 'kraken', name: 'Kraken' }]);

      expect(get(status.shouldFetchEventsRegularly)).toBe(false);
    });

    it('should be on while a transaction sync runs outside a history refresh', async () => {
      const { orchestrator, status, types } = await setup();

      orchestrator.submit({
        id: types.makeActivityId(types.ActivityKind.TX_SYNC, 'eth', '0x123'),
        kind: types.ActivityKind.TX_SYNC,
        run: async (): Promise<Result<unknown, TaskError>> => neverSettles(),
        title: 'eth',
      });

      expect(get(status.shouldFetchEventsRegularly)).toBe(true);
    });
  });
});
