import type { Result } from 'plainfp/result';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { neverSettles } from '@test/utils/never-settles';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed } from 'vue';
import { useBalanceStatus } from '@/modules/balances/use-balance-status';
import { useLocationBalanceStatus } from '@/modules/balances/use-location-balance-status';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    matchChain: (location: string): string | undefined => (location === 'eth' ? 'eth' : undefined),
  })),
}));

vi.mock('@/modules/balances/use-balance-status', () => ({
  useBalanceStatus: vi.fn(() => ({
    isInitialLoading: computed<boolean>(() => true),
    isRefreshing: computed<boolean>(() => false),
  })),
}));

/** Work that never settles, so it stays active for as long as the test needs it. */
function start(kind: ActivityKind, ...parts: string[]): void {
  useTaskOrchestrator().submit({
    id: makeActivityId(kind, ...parts),
    kind,
    run: async (): Promise<Result<unknown, TaskError>> => neverSettles(),
    title: kind,
  });
}

describe('useLocationBalanceStatus', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    // The orchestrator is a shared singleton, so its ledger outlives a test without this.
    useTaskOrchestrator().reset();
    vi.mocked(useBalanceStatus).mockClear();
    const { allLocations } = storeToRefs(useLocationStore());
    set(allLocations, {
      kraken: { isExchange: true, label: 'Kraken' },
      binance: { isExchange: true, label: 'Binance' },
      cash: { label: 'Cash' },
    });
    useBankConnectionsStore().setConnections([{
      connector: 'fints',
      displayName: 'FinTS',
      identifier: 'c1',
      location: 'custom:ing',
      name: 'main',
      syncStatus: { authChallenge: null, authExpired: false, lastError: null, lastSyncTs: null, running: false },
    }]);
  });

  it('should answer a chain from its own balance status', () => {
    const { isInitialLoading, isRefreshing } = useLocationBalanceStatus('eth');

    expect(useBalanceStatus).toHaveBeenCalledWith('eth');
    expect(get(isInitialLoading)).toBe(true);
    expect(get(isRefreshing)).toBe(false);
  });

  it('should answer an exchange from the activity keyed by its location', () => {
    const { isInitialLoading, isRefreshing } = useLocationBalanceStatus('kraken');
    expect(get(isInitialLoading)).toBe(false);

    start(ActivityKind.EXCHANGE_BALANCES, 'binance');
    expect(get(isInitialLoading)).toBe(false);

    start(ActivityKind.EXCHANGE_BALANCES, 'kraken');
    expect(get(isInitialLoading)).toBe(true);
    expect(get(isRefreshing)).toBe(false);
    expect(useBalanceStatus).not.toHaveBeenCalled();
  });

  it('should report a refresh once the exchange has loaded before', () => {
    const { isInitialLoading, isRefreshing } = useLocationBalanceStatus('kraken');

    useTaskOrchestrator().markCompleted(ActivityKind.EXCHANGE_BALANCES, 'kraken');
    start(ActivityKind.EXCHANGE_BALANCES, 'kraken');

    expect(get(isInitialLoading)).toBe(false);
    expect(get(isRefreshing)).toBe(true);
  });

  it('should answer a bank from the bank refresh, not the exchange one', () => {
    const { isInitialLoading } = useLocationBalanceStatus('custom:ing');

    start(ActivityKind.EXCHANGE_BALANCES, 'custom:ing');
    expect(get(isInitialLoading)).toBe(false);

    start(ActivityKind.BANK_BALANCES);
    expect(get(isInitialLoading)).toBe(true);
  });

  it('should answer any other location from the manual balances', () => {
    const { isInitialLoading, isRefreshing } = useLocationBalanceStatus('cash');

    start(ActivityKind.BANK_BALANCES);
    expect(get(isInitialLoading)).toBe(false);

    useTaskOrchestrator().markCompleted(ActivityKind.MANUAL_BALANCES);
    start(ActivityKind.MANUAL_BALANCES);
    expect(get(isInitialLoading)).toBe(false);
    expect(get(isRefreshing)).toBe(true);
  });
});
