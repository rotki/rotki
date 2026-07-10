import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useEthStakingRefresh } from '@/modules/staking/eth/use-eth-staking-refresh';

const mockFetchEthStakingValidators = vi.fn();
const mockFetchBlockchainBalances = vi.fn();
const mockRefreshBlockchainBalances = vi.fn();
const mockIsFirstLoad = vi.fn((): boolean => false);
const { mockLoggerLog } = vi.hoisted(() => ({ mockLoggerLog: vi.fn() }));

const mockUsername = ref<string>('test-user');
const mockStakingValidatorsLimits = ref<{ limit: number; total: number }>();
const mockPerformanceRefreshing = ref<boolean>(false);
const mockEth2Loading = ref<boolean>(false);
const mockBlockProductionLoading = ref<boolean>(false);

vi.mock('@/modules/accounts/use-eth-staking', () => ({
  useEthStaking: vi.fn(() => ({
    fetchEthStakingValidators: mockFetchEthStakingValidators,
  })),
}));

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: vi.fn(() => ({
    username: mockUsername,
  })),
}));

vi.mock('@/modules/balances/use-blockchain-balances', () => ({
  useBlockchainBalances: vi.fn(() => ({
    fetchBlockchainBalances: mockFetchBlockchainBalances,
    refreshBlockchainBalances: mockRefreshBlockchainBalances,
  })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: {
    log: mockLoggerLog,
  },
}));

vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: vi.fn(() => ({
    useIsTaskRunning: vi.fn(() => mockBlockProductionLoading),
  })),
}));

vi.mock('@/modules/shell/sync-progress/use-section-status', () => ({
  useSectionStatus: vi.fn((_section: unknown, subsection?: unknown) => ({
    isLoading: subsection === undefined ? mockPerformanceRefreshing : mockEth2Loading,
  })),
}));

vi.mock('@/modules/shell/sync-progress/use-status-updater', () => ({
  useStatusUpdater: vi.fn(() => ({
    isFirstLoad: mockIsFirstLoad,
  })),
}));

vi.mock('@/modules/staking/use-blockchain-validators-store', () => ({
  useBlockchainValidatorsStore: vi.fn(() => ({
    stakingValidatorsLimits: mockStakingValidatorsLimits,
  })),
}));

interface RefreshCallbacks {
  getPerformance: () => { entriesTotal: number };
  refreshPerformance: (userInitiated: boolean) => Promise<void>;
  setTotal: () => void;
}

function createCallbacks(overrides: {
  entriesTotal?: number;
  refreshPerformance?: RefreshCallbacks['refreshPerformance'];
  setTotal?: RefreshCallbacks['setTotal'];
} = {}): RefreshCallbacks {
  return {
    getPerformance: vi.fn((): { entriesTotal: number } => ({ entriesTotal: overrides.entriesTotal ?? 0 })),
    refreshPerformance: overrides.refreshPerformance ?? vi.fn(async (): Promise<void> => {}),
    setTotal: overrides.setTotal ?? vi.fn(),
  };
}

describe('useEthStakingRefresh', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsFirstLoad.mockReturnValue(false);
    set(mockUsername, 'test-user');
    set(mockStakingValidatorsLimits, undefined);
    set(mockPerformanceRefreshing, false);
    set(mockEth2Loading, false);
    set(mockBlockProductionLoading, false);
    mockFetchEthStakingValidators.mockResolvedValue(undefined);
    mockFetchBlockchainBalances.mockResolvedValue(undefined);
    mockRefreshBlockchainBalances.mockResolvedValue(undefined);
  });

  describe('refresh', () => {
    it('should force a balance refresh when user initiated', async () => {
      const { refresh } = useEthStakingRefresh(createCallbacks());
      await refresh(true);

      expect(mockRefreshBlockchainBalances).toHaveBeenCalledWith({ blockchain: 'eth2' });
      expect(mockFetchBlockchainBalances).not.toHaveBeenCalled();
      expect(mockFetchEthStakingValidators).toHaveBeenCalledWith({ ignoreCache: true });
    });

    it('should force a balance refresh on first load even when not user initiated', async () => {
      mockIsFirstLoad.mockReturnValue(true);

      const { refresh } = useEthStakingRefresh(createCallbacks());
      await refresh(false);

      expect(mockRefreshBlockchainBalances).toHaveBeenCalledWith({ blockchain: 'eth2' });
      expect(mockFetchBlockchainBalances).not.toHaveBeenCalled();
      expect(mockFetchEthStakingValidators).toHaveBeenCalledWith({ ignoreCache: true });
    });

    it('should use cached balances when not user initiated and not first load', async () => {
      const { refresh } = useEthStakingRefresh(createCallbacks());
      await refresh(false);

      expect(mockFetchBlockchainBalances).toHaveBeenCalledWith({ blockchain: 'eth2' });
      expect(mockRefreshBlockchainBalances).not.toHaveBeenCalled();
      expect(mockFetchEthStakingValidators).toHaveBeenCalledWith({ ignoreCache: false });
    });

    it('should default userInitiated to false', async () => {
      const { refresh } = useEthStakingRefresh(createCallbacks());
      await refresh();

      expect(mockFetchBlockchainBalances).toHaveBeenCalledWith({ blockchain: 'eth2' });
      expect(mockRefreshBlockchainBalances).not.toHaveBeenCalled();
    });

    it('should set the total after refreshing validators', async () => {
      const setTotal = vi.fn();
      const { refresh } = useEthStakingRefresh(createCallbacks({ setTotal }));
      await refresh(false);

      expect(setTotal).toHaveBeenCalledOnce();
    });

    it('should refresh performance once when validators do not exceed entries', async () => {
      const refreshPerformance = vi.fn(async (): Promise<void> => {});
      set(mockStakingValidatorsLimits, { limit: 10, total: 5 });

      const { refresh } = useEthStakingRefresh(createCallbacks({ entriesTotal: 5, refreshPerformance }));
      await refresh(false);

      expect(refreshPerformance).toHaveBeenCalledTimes(1);
      expect(refreshPerformance).toHaveBeenCalledWith(false);
      expect(mockLoggerLog).not.toHaveBeenCalled();
    });

    it('should force a second performance refresh when validators exceed entries', async () => {
      const refreshPerformance = vi.fn(async (): Promise<void> => {});
      set(mockStakingValidatorsLimits, { limit: 10, total: 8 });

      const { refresh } = useEthStakingRefresh(createCallbacks({ entriesTotal: 3, refreshPerformance }));
      await refresh(true);

      expect(refreshPerformance).toHaveBeenCalledTimes(2);
      expect(refreshPerformance).toHaveBeenNthCalledWith(1, true);
      expect(refreshPerformance).toHaveBeenNthCalledWith(2, true);
      expect(mockLoggerLog).toHaveBeenCalledOnce();
    });

    it('should treat missing validator limits as zero total', async () => {
      const refreshPerformance = vi.fn(async (): Promise<void> => {});
      set(mockStakingValidatorsLimits, undefined);

      const { refresh } = useEthStakingRefresh(createCallbacks({ entriesTotal: 0, refreshPerformance }));
      await refresh(false);

      expect(refreshPerformance).toHaveBeenCalledTimes(1);
      expect(mockLoggerLog).not.toHaveBeenCalled();
    });

    it('should update lastRefresh timestamp after a successful refresh', async () => {
      const { lastRefresh, refresh } = useEthStakingRefresh(createCallbacks());
      set(lastRefresh, 0);
      await refresh(false);

      expect(get(lastRefresh)).toBeGreaterThan(0);
    });
  });

  describe('loading states', () => {
    it('should expose block production loading state', () => {
      const { blockProductionLoading } = useEthStakingRefresh(createCallbacks());
      set(mockBlockProductionLoading, true);

      expect(get(blockProductionLoading)).toBe(true);
    });

    it('should expose performance refreshing state', () => {
      const { performanceRefreshing } = useEthStakingRefresh(createCallbacks());
      set(mockPerformanceRefreshing, true);

      expect(get(performanceRefreshing)).toBe(true);
    });

    it('should be refreshing when performance is refreshing', () => {
      const { refreshing } = useEthStakingRefresh(createCallbacks());
      set(mockPerformanceRefreshing, true);

      expect(get(refreshing)).toBe(true);
    });

    it('should be refreshing when eth2 balances are loading', () => {
      const { refreshing } = useEthStakingRefresh(createCallbacks());
      set(mockEth2Loading, true);

      expect(get(refreshing)).toBe(true);
    });

    it('should be refreshing when block production is loading', () => {
      const { refreshing } = useEthStakingRefresh(createCallbacks());
      set(mockBlockProductionLoading, true);

      expect(get(refreshing)).toBe(true);
    });

    it('should not be refreshing when nothing is loading', () => {
      const { refreshing } = useEthStakingRefresh(createCallbacks());

      expect(get(refreshing)).toBe(false);
    });
  });
});
