import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Module } from '@/modules/common/modules';
import { Section, Status } from '@/modules/common/status';
import { TaskType } from '@/modules/tasks/task-type';
import { usePoolDataFetching } from './use-pool-data-fetching';
import '@test/i18n';

const mockRunTask = vi.fn();
const mockIsTaskRunning = vi.fn();
const mockGetUniswapV2Balances = vi.fn();
const mockGetSushiswapBalances = vi.fn();

vi.mock('@/modules/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: vi.fn((): Record<string, unknown> => ({
    runTask: mockRunTask,
  })),
}));

vi.mock('@/modules/tasks/use-task-store', () => ({
  useTaskStore: vi.fn((): Record<string, unknown> => ({
    isTaskRunning: mockIsTaskRunning,
  })),
}));

vi.mock('./use-pool-api', () => ({
  usePoolApi: vi.fn((): Record<string, unknown> => ({
    getUniswapV2Balances: mockGetUniswapV2Balances,
    getSushiswapBalances: mockGetSushiswapBalances,
  })),
}));

const mockIsPremium = vi.fn((): Ref<boolean> => ref<boolean>(true));
vi.mock('@/composables/premium', () => ({
  usePremium: (): Ref<boolean> => mockIsPremium(),
}));

const mockActiveModules = vi.fn((): Ref<string[]> => ref<string[]>([Module.UNISWAP, Module.SUSHISWAP]));
vi.mock('@/store/settings/general', () => ({
  useGeneralSettingsStore: vi.fn((): Record<string, unknown> => ({
    activeModules: mockActiveModules(),
  })),
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
    mockIsTaskRunning.mockReturnValue(false);
    mockRunTask.mockResolvedValue({ success: false, cancelled: true });
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

      expect(mockRunTask).toHaveBeenCalledTimes(2);
      const [, uniOptions] = mockRunTask.mock.calls[0];
      const [, sushiOptions] = mockRunTask.mock.calls[1];
      expect(uniOptions.type).toBe(TaskType.UNISWAP_V2_BALANCES);
      expect(sushiOptions.type).toBe(TaskType.SUSHISWAP_BALANCES);
    });

    it('should skip sushiswap when not premium', async () => {
      mockIsPremium.mockReturnValue(ref<boolean>(false));

      const { fetch } = usePoolDataFetching();
      await fetch();

      expect(mockRunTask).toHaveBeenCalledOnce();
      const [, options] = mockRunTask.mock.calls[0];
      expect(options.type).toBe(TaskType.UNISWAP_V2_BALANCES);
    });

    it('should skip when uniswap module is not active', async () => {
      mockActiveModules.mockReturnValue(ref<string[]>([]));

      const { fetch } = usePoolDataFetching();
      await fetch();

      expect(mockRunTask).not.toHaveBeenCalled();
    });

    it('should skip when task is already running', async () => {
      mockIsTaskRunning.mockReturnValue(true);

      const { fetch } = usePoolDataFetching();
      await fetch();

      expect(mockRunTask).not.toHaveBeenCalled();
    });

    it('should skip when already loaded and not refreshing', async () => {
      const { useStatusStore } = await import('@/store/status');
      const statusStore = useStatusStore();
      statusStore.setStatus({ status: Status.LOADED, section: Section.POOLS_UNISWAP_V2 });
      statusStore.setStatus({ status: Status.LOADED, section: Section.POOLS_SUSHISWAP });

      const { fetch } = usePoolDataFetching();
      await fetch();

      expect(mockRunTask).not.toHaveBeenCalled();
    });

    it('should fetch when refreshing even if already loaded', async () => {
      const { useStatusStore } = await import('@/store/status');
      const statusStore = useStatusStore();
      statusStore.setStatus({ status: Status.LOADED, section: Section.POOLS_UNISWAP_V2 });
      statusStore.setStatus({ status: Status.LOADED, section: Section.POOLS_SUSHISWAP });

      const { fetch } = usePoolDataFetching();
      await fetch(true);

      expect(mockRunTask).toHaveBeenCalledTimes(2);
    });
  });
});
