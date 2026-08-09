import type { Result } from 'plainfp/result';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { beforeEach, describe, expect, it } from 'vitest';
import { ref } from 'vue';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { useBalanceStatus } from '@/modules/balances/use-balance-status';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

/** A fetch that never settles, so the chain stays live for as long as the test needs it. */
function startFetch(chain: string, ...parts: string[]): void {
  useTaskOrchestrator().submit({
    id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, chain, ...parts),
    kind: ActivityKind.BLOCKCHAIN_BALANCES,
    run: async (): Promise<Result<unknown, TaskError>> => new Promise(() => {}),
    title: chain,
  });
}

function markLoaded(chain: string): void {
  useTaskOrchestrator().markCompleted(ActivityKind.BLOCKCHAIN_BALANCES, chain);
}

describe('useBalanceStatus', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    // The orchestrator is a shared singleton, so its ledger outlives a test without this.
    useTaskOrchestrator().reset();
  });

  describe('per-chain', () => {
    it('should report nothing loaded and nothing running for an untouched chain', () => {
      const { hasCachedData, isInitialLoading, isRefreshing } = useBalanceStatus('eth');
      expect(get(hasCachedData)).toBe(false);
      expect(get(isInitialLoading)).toBe(false);
      expect(get(isRefreshing)).toBe(false);
    });

    it('should report initial loading only until the chain has data', () => {
      const { hasCachedData, isInitialLoading } = useBalanceStatus('eth');

      startFetch('eth');
      expect(get(hasCachedData)).toBe(false);
      expect(get(isInitialLoading)).toBe(true);

      markLoaded('eth');
      expect(get(hasCachedData)).toBe(true);
      expect(get(isInitialLoading)).toBe(false);
    });

    /**
     * 🔴 Hydration is not an activity, so the orchestrator reports a chain being read from the DB
     * as idle. Without the store half, the whole cached phase renders settled-and-empty.
     */
    it('should cover a chain being hydrated as well as refreshed', () => {
      const refreshState = useBalanceRefreshState();
      const { isInitialLoading } = useBalanceStatus('eth');

      expect(get(isInitialLoading)).toBe(false);

      refreshState.startHydration('eth');
      expect(get(isInitialLoading)).toBe(true);

      refreshState.stopHydration('eth');
      expect(get(isInitialLoading)).toBe(false);
    });

    it('should not mistake a sibling chain\'s hydration for this one', () => {
      const refreshState = useBalanceRefreshState();
      const { isInitialLoading } = useBalanceStatus('eth');

      refreshState.startHydration('btc');
      expect(get(isInitialLoading)).toBe(false);
    });

    it('should not mistake a sibling chain for this one', () => {
      const { hasCachedData } = useBalanceStatus('eth');

      markLoaded('ethereum_beaconchain');
      expect(get(hasCachedData)).toBe(false);
    });

    it('should track refresh independently of cache status', () => {
      const refreshState = useBalanceRefreshState();
      const { hasCachedData, isRefreshing } = useBalanceStatus('eth');

      markLoaded('eth');
      refreshState.start('eth');

      expect(get(hasCachedData)).toBe(true);
      expect(get(isRefreshing)).toBe(true);

      refreshState.stop('eth');
      expect(get(hasCachedData)).toBe(true);
      expect(get(isRefreshing)).toBe(false);
    });

    it('should react to a reactive chain argument', () => {
      const chain = ref<string>('eth');
      const { hasCachedData } = useBalanceStatus(chain);

      markLoaded('eth');
      expect(get(hasCachedData)).toBe(true);

      set(chain, 'optimism');
      expect(get(hasCachedData)).toBe(false);

      markLoaded('optimism');
      expect(get(hasCachedData)).toBe(true);
    });
  });

  describe('aggregate', () => {
    it('should be false/false when no chain has been touched', () => {
      const { hasCachedData, isInitialLoading, isRefreshing } = useBalanceStatus();
      expect(get(hasCachedData)).toBe(false);
      expect(get(isInitialLoading)).toBe(false);
      expect(get(isRefreshing)).toBe(false);
    });

    it('should report hasCachedData when at least one chain has loaded', () => {
      const { hasCachedData } = useBalanceStatus();

      startFetch('eth');
      startFetch('optimism');
      expect(get(hasCachedData)).toBe(false);

      markLoaded('eth');
      expect(get(hasCachedData)).toBe(true);
    });

    it('should stop reporting initial loading once the first chain has data', () => {
      const { isInitialLoading } = useBalanceStatus();

      startFetch('eth');
      startFetch('optimism');
      expect(get(isInitialLoading)).toBe(true);

      // There is now something to show, so the initial-loading screen has nothing left to cover
      // even though optimism is still fetching. That chain's own spinner takes over.
      markLoaded('eth');
      expect(get(isInitialLoading)).toBe(false);
    });

    it('should report isRefreshing when any chain has a refresh in flight', () => {
      const refreshState = useBalanceRefreshState();
      const { isRefreshing } = useBalanceStatus();

      refreshState.start('eth');
      expect(get(isRefreshing)).toBe(true);

      refreshState.start('optimism');
      refreshState.stop('eth');
      expect(get(isRefreshing)).toBe(true);

      refreshState.stop('optimism');
      expect(get(isRefreshing)).toBe(false);
    });
  });
});
