import { neverSettles } from '@test/utils/never-settles';
import { err, type Result } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { useBalanceStatus, useChainLoadStates } from '@/modules/balances/use-balance-status';
import { Skipped, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

/** A fetch that never settles, so the chain stays live for as long as the test needs it. */
function startFetch(chain: string, ...parts: string[]): void {
  useTaskOrchestrator().submit({
    id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, chain, ...parts),
    kind: ActivityKind.BLOCKCHAIN_BALANCES,
    run: async (): Promise<Result<unknown, TaskError>> => neverSettles(),
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

    it('should read loading from the store for a hydrating chain, which the orchestrator calls idle', () => {
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

describe('useChainLoadStates', () => {
  /** A fetch that ends at once with the given outcome. */
  async function settleFetch(chain: string, outcome: Result<unknown, TaskError>): Promise<void> {
    useTaskOrchestrator().submit({
      id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, chain),
      kind: ActivityKind.BLOCKCHAIN_BALANCES,
      run: async (): Promise<Result<unknown, TaskError>> => outcome,
      title: chain,
    });
    await vi.waitFor(() => expect(useTaskOrchestrator().statusOfPrefix(ActivityKind.BLOCKCHAIN_BALANCES, chain).active).toBe(false));
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    useTaskOrchestrator().reset();
  });

  it('should count every chain that has never loaded as loading until the login load settles, when asked to', () => {
    expect(get(useChainLoadStates(['eth', 'gnosis'], { untilFirstLoad: true }).loading)).toStrictEqual(['eth', 'gnosis']);
    expect(get(useChainLoadStates(['eth', 'gnosis']).loading)).toStrictEqual([]);
  });

  it('should count a chain as loading only while it is read for the first time', () => {
    useBalanceRefreshState().settleFirstLoad();
    const { loading } = useChainLoadStates(['eth', 'gnosis', 'base'], { untilFirstLoad: true });
    startFetch('eth');
    useBalanceRefreshState().startHydration('gnosis');

    expect(get(loading)).toStrictEqual(['eth', 'gnosis']);
  });

  it('should not count a chain that loaded before as loading when it refreshes again', () => {
    markLoaded('eth');
    startFetch('eth');

    expect(get(useChainLoadStates(['eth']).loading)).toStrictEqual([]);
  });

  it('should call unloaded a chain that never loaded or whose last load failed, but not one switched off', async () => {
    useBalanceRefreshState().settleFirstLoad();
    markLoaded('eth');
    markLoaded('base');
    await settleFetch('base', err(TaskFailed({ message: 'rpc down' })));
    await settleFetch('gnosis', err(Skipped({ message: 'disabled in settings' })));

    expect(get(useChainLoadStates(['eth', 'base', 'gnosis', 'monad']).unloaded)).toStrictEqual(['base', 'monad']);
  });
});
