import { createCustomPinia } from '@test/utils/create-pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ActivityKind, type WorkStatus } from '@/modules/task-center/core/types';
import { useBalancesLoading } from './use-balance-loading';
import { useBalanceRefreshState } from './use-balance-refresh-state';

const activeKinds = ref<Set<ActivityKind>>(new Set());

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): object => ({
    useIsActive: (kind: ActivityKind) => computed<boolean>(() => get(activeKinds).has(kind)),
    useWorkStatus: (kind: ActivityKind) => computed<Partial<WorkStatus>>(() => ({ active: get(activeKinds).has(kind) })),
  }),
}));

describe('useBalancesLoading', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    set(activeKinds, new Set());
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should not be loading when no relevant task runs', () => {
    const { loadingBalances, loadingBalancesAndDetection } = useBalancesLoading();
    expect(get(loadingBalances)).toBe(false);
    expect(get(loadingBalancesAndDetection)).toBe(false);
  });

  it.each([
    ActivityKind.BLOCKCHAIN_BALANCES,
    ActivityKind.EXCHANGE_BALANCES,
    ActivityKind.ALL_BALANCES,
    ActivityKind.MANUAL_BALANCES,
  ])('should flag loading when activity %s is active', (kind) => {
    const { loadingBalances, loadingBalancesAndDetection } = useBalancesLoading();
    set(activeKinds, new Set([kind]));
    expect(get(loadingBalances)).toBe(true);
    expect(get(loadingBalancesAndDetection)).toBe(true);
  });

  it('should include token detection only in the detection flag', () => {
    const { loadingBalances, loadingBalancesAndDetection } = useBalancesLoading();
    set(activeKinds, new Set([ActivityKind.TOKEN_DETECTION]));
    expect(get(loadingBalances)).toBe(false);
    expect(get(loadingBalancesAndDetection)).toBe(true);
  });

  it('should flag loading while a chain is hydrating, even though hydration has no activity', () => {
    const { loadingBalances, loadingBlockchainBalances } = useBalancesLoading();
    expect(get(activeKinds).size).toBe(0);
    expect(get(loadingBlockchainBalances)).toBe(false);

    useBalanceRefreshState().startHydration('eth');

    expect(get(loadingBlockchainBalances)).toBe(true);
    expect(get(loadingBalances)).toBe(true);
  });
});
