import { runSpecWith } from '@test/utils/mocks/native-task';
import { createPinia, setActivePinia } from 'pinia';
import { err, ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Module } from '@/modules/core/common/modules';
import { Cancelled } from '@/modules/core/tasks/task-result';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { usePoolDataFetching } from './use-pool-data-fetching';
import '@test/i18n';

const mockRunTaskResult = vi.fn();
const mockStatusOf = vi.fn();
const mockGetUniswapV2Balances = vi.fn();
const mockGetSushiswapBalances = vi.fn();

/** Runs the submitted spec inline so assertions see the real `run` body. */
const mockSubmitTask = vi.fn(runSpecWith(mockRunTaskResult));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn((): Record<string, unknown> => ({
    cancelByType: vi.fn(() => vi.fn()),
    runTaskResult: mockRunTaskResult,
    statusOf: mockStatusOf,
    submitTask: mockSubmitTask,
  })),
}));

const IDLE = { active: false, everCompleted: false, pending: false, running: false };

vi.mock('./use-pool-api', () => ({
  usePoolApi: vi.fn((): Record<string, unknown> => ({
    getUniswapV2Balances: mockGetUniswapV2Balances,
    getSushiswapBalances: mockGetSushiswapBalances,
  })),
}));

const mockIsPremium = vi.fn((): Ref<boolean> => ref<boolean>(true));
vi.mock('@/modules/premium/use-premium', () => ({
  usePremium: (): Ref<boolean> => mockIsPremium(),
}));

const mockActiveModules = vi.fn((): Ref<string[]> => ref<string[]>([Module.UNISWAP, Module.SUSHISWAP]));
vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<string[]> => mockActiveModules(),
}));

vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: vi.fn((): Record<string, unknown> => ({
    addresses: ref<Record<string, string[]>>({ eth: ['0x123'] }),
  })),
}));

vi.mock('@/modules/accounts/use-blockchain-accounts-store', () => ({
  useBlockchainAccountsStore: vi.fn((): Record<string, unknown> => ({
    recentlyAddedAddresses: ref(new Set<string>()),
  })),
}));

describe('usePoolDataFetching', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockStatusOf.mockReturnValue(IDLE);
    mockRunTaskResult.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));
    mockIsPremium.mockReturnValue(ref<boolean>(true));
    mockActiveModules.mockReturnValue(ref<string[]>([Module.UNISWAP, Module.SUSHISWAP]));
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('fetch', () => {
    it('should fetch both uniswap and sushiswap when premium', async () => {
      const { fetch } = usePoolDataFetching();
      await fetch();

      expect(mockRunTaskResult).toHaveBeenCalledTimes(2);
    });

    it('should submit one native activity per protocol', async () => {
      const { fetch } = usePoolDataFetching();
      await fetch();

      expect(mockSubmitTask).toHaveBeenCalledTimes(2);
      const [uniSpec] = mockSubmitTask.mock.calls[0];
      const [sushiSpec] = mockSubmitTask.mock.calls[1];
      expect(uniSpec.kind).toBe(ActivityKind.LIQUIDITY_POOLS);
      expect(uniSpec.id).toBe(`${ActivityKind.LIQUIDITY_POOLS}:${ActivityPart.UNISWAP_V2}`);
      expect(sushiSpec.id).toBe(`${ActivityKind.LIQUIDITY_POOLS}:${ActivityPart.SUSHISWAP}`);
    });

    it('should store parsed balances on success', async () => {
      const balances = { '0x123': [{ address: '0x456', assets: [], totalAmount: '1', usdPrice: '2', userBalance: { amount: '1', usdValue: '2' } }] };
      mockRunTaskResult.mockResolvedValue(ok(balances));

      const { usePoolBalancesStore } = await import('./use-pool-balances-store');
      const store = usePoolBalancesStore();

      const { fetch } = usePoolDataFetching();
      await fetch();

      // The parsed payload lands in the store for both protocols, not just the task being run.
      expect(Object.keys(get(store.uniswapPoolBalances))).toEqual(['0x123']);
      expect(Object.keys(get(store.sushiswapPoolBalances))).toEqual(['0x123']);
    });

    it('should skip sushiswap when not premium', async () => {
      mockIsPremium.mockReturnValue(ref<boolean>(false));

      const { fetch } = usePoolDataFetching();
      await fetch();

      expect(mockRunTaskResult).toHaveBeenCalledOnce();
    });

    it('should skip when uniswap module is not active', async () => {
      mockActiveModules.mockReturnValue(ref<string[]>([]));

      const { fetch } = usePoolDataFetching();
      await fetch();

      expect(mockRunTaskResult).not.toHaveBeenCalled();
    });

    it('should skip when the activity is already active', async () => {
      mockStatusOf.mockReturnValue({ ...IDLE, active: true, running: true });

      const { fetch } = usePoolDataFetching();
      await fetch();

      expect(mockSubmitTask).not.toHaveBeenCalled();
    });

    it('should skip when already completed and not refreshing', async () => {
      mockStatusOf.mockReturnValue({ ...IDLE, everCompleted: true });

      const { fetch } = usePoolDataFetching();
      await fetch();

      expect(mockSubmitTask).not.toHaveBeenCalled();
    });

    it('should fetch when refreshing even if already completed', async () => {
      mockStatusOf.mockReturnValue({ ...IDLE, everCompleted: true });

      const { fetch } = usePoolDataFetching();
      await fetch(true);

      expect(mockSubmitTask).toHaveBeenCalledTimes(2);
    });
  });
});
