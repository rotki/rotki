import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockFetchDetectedTokens = vi.fn();
vi.mock('@/modules/balances/blockchain/use-token-detection-api', () => ({
  useTokenDetectionApi: vi.fn().mockReturnValue({
    fetchDetectedTokens: mockFetchDetectedTokens,
  }),
}));

vi.mock('@/modules/balances/blockchain/use-token-detection-store', () => ({
  useTokenDetectionStore: vi.fn().mockReturnValue({
    massDetecting: ref<string>(),
    setMassDetecting: vi.fn(),
  }),
}));

const mockAddresses = ref<Record<string, string[]>>({});
vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: vi.fn().mockReturnValue({
    addresses: mockAddresses,
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    supportsTransactions: (chain: string): boolean => chain !== 'btc',
    txEvmChains: computed(() => [
      { id: 'eth' },
      { id: 'optimism' },
    ]),
  }),
}));

const mockRefreshBlockchainBalances = vi.fn().mockResolvedValue(undefined);
vi.mock('@/modules/balances/use-blockchain-balances', () => ({
  useBlockchainBalances: vi.fn().mockReturnValue({
    refreshBlockchainBalances: mockRefreshBlockchainBalances,
  }),
}));

const mockQueueTokenDetection = vi.fn().mockImplementation(
  async (_chain: string, addrs: string[], fn: (addr: string) => Promise<void>): Promise<void> => {
    for (const addr of addrs)
      await fn(addr);
  },
);
vi.mock('@/modules/balances/use-balance-queue', () => ({
  useBalanceQueue: vi.fn().mockReturnValue({
    queueTokenDetection: mockQueueTokenDetection,
  }),
}));

const mockIsTaskRunning = vi.fn().mockReturnValue(false);
vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    isTaskRunning: mockIsTaskRunning,
  }),
}));

// Must use dynamic import + resetModules because createSharedComposable caches the instance
async function loadOrchestrator(): Promise<typeof import('./use-token-detection-orchestrator')> {
  vi.resetModules();
  return import('./use-token-detection-orchestrator');
}

describe('useTokenDetectionOrchestrator', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsTaskRunning.mockReturnValue(false);
    set(mockAddresses, {});
  });

  describe('detectTokens', () => {
    it('should queue detection and refresh balances for a single chain', async () => {
      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { detectTokens } = useTokenDetectionOrchestrator();

      await detectTokens('eth', ['0xaddr1', '0xaddr2']);

      expect(mockQueueTokenDetection).toHaveBeenCalledOnce();
      expect(mockQueueTokenDetection).toHaveBeenCalledWith('eth', ['0xaddr1', '0xaddr2'], expect.any(Function));
      expect(mockFetchDetectedTokens).toHaveBeenCalledWith('eth', '0xaddr1');
      expect(mockFetchDetectedTokens).toHaveBeenCalledWith('eth', '0xaddr2');
      expect(mockRefreshBlockchainBalances).toHaveBeenCalledWith({
        blockchain: 'eth',
      });
    });

    it('should queue detection for multiple chains', async () => {
      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { detectTokens } = useTokenDetectionOrchestrator();

      await detectTokens(['eth', 'optimism'], ['0xaddr1']);

      expect(mockQueueTokenDetection).toHaveBeenCalledTimes(2);
      expect(mockRefreshBlockchainBalances).toHaveBeenCalledTimes(2);
    });

    it('should skip balance refresh when option is false', async () => {
      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { detectTokens } = useTokenDetectionOrchestrator();

      await detectTokens('eth', ['0xaddr1'], { refreshBalancesAfter: false });

      expect(mockQueueTokenDetection).toHaveBeenCalledOnce();
      expect(mockRefreshBlockchainBalances).not.toHaveBeenCalled();
    });

    it('should filter out addresses already being detected', async () => {
      mockIsTaskRunning.mockImplementation((_type: unknown, meta: { chain: string; address?: string }): boolean =>
        meta.address === '0xaddr1',
      );

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { detectTokens } = useTokenDetectionOrchestrator();

      await detectTokens('eth', ['0xaddr1', '0xaddr2']);

      // Only 0xaddr2 should be queued since 0xaddr1 is already detecting
      expect(mockQueueTokenDetection).toHaveBeenCalledWith('eth', ['0xaddr2'], expect.any(Function));
    });

    it('should skip queueing when all addresses are already detecting', async () => {
      mockIsTaskRunning.mockReturnValue(true);

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { detectTokens } = useTokenDetectionOrchestrator();

      await detectTokens('eth', ['0xaddr1']);

      // No addresses left to queue, but balance refresh still happens
      expect(mockQueueTokenDetection).not.toHaveBeenCalled();
      expect(mockRefreshBlockchainBalances).toHaveBeenCalledOnce();
    });
  });

  describe('detectAllTokens', () => {
    it('should detect tokens for all tx evm chains when no chain specified', async () => {
      set(mockAddresses, {
        eth: ['0xaddr1'],
        optimism: ['0xaddr2'],
      });

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { detectAllTokens } = useTokenDetectionOrchestrator();

      await detectAllTokens();

      expect(mockQueueTokenDetection).toHaveBeenCalledTimes(2);
      expect(mockRefreshBlockchainBalances).toHaveBeenCalledTimes(2);
    });

    it('should detect tokens only for specified chains', async () => {
      set(mockAddresses, {
        eth: ['0xaddr1'],
        optimism: ['0xaddr2'],
      });

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { detectAllTokens } = useTokenDetectionOrchestrator();

      await detectAllTokens('eth');

      expect(mockQueueTokenDetection).toHaveBeenCalledOnce();
      expect(mockQueueTokenDetection).toHaveBeenCalledWith('eth', ['0xaddr1'], expect.any(Function));
    });

    it('should skip chains without addresses', async () => {
      set(mockAddresses, {
        eth: ['0xaddr1'],
        // optimism has no addresses
      });

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { detectAllTokens } = useTokenDetectionOrchestrator();

      await detectAllTokens();

      expect(mockQueueTokenDetection).toHaveBeenCalledOnce();
    });

    it('should skip chains that do not support transactions', async () => {
      set(mockAddresses, {
        btc: ['bc1qaddr1'],
        eth: ['0xaddr1'],
      });

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { detectAllTokens } = useTokenDetectionOrchestrator();

      await detectAllTokens(['btc', 'eth']);

      // Only eth should be queued — btc does not support transactions
      expect(mockQueueTokenDetection).toHaveBeenCalledOnce();
      expect(mockQueueTokenDetection).toHaveBeenCalledWith('eth', ['0xaddr1'], expect.any(Function));
    });
  });

  describe('useIsDetecting', () => {
    it('should return false when no detection is running', async () => {
      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { useIsDetecting } = useTokenDetectionOrchestrator();

      const detecting = useIsDetecting('eth');
      expect(get(detecting)).toBe(false);
    });

    it('should return true when detection is running for the chain', async () => {
      mockIsTaskRunning.mockReturnValue(true);

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { useIsDetecting } = useTokenDetectionOrchestrator();

      const detecting = useIsDetecting('eth');
      expect(get(detecting)).toBe(true);
    });

    it('should check specific address when provided', async () => {
      mockIsTaskRunning.mockImplementation((_type: unknown, meta: { chain: string; address?: string }): boolean =>
        meta.address === '0xaddr1',
      );

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { useIsDetecting } = useTokenDetectionOrchestrator();

      const detecting = useIsDetecting('eth', '0xaddr1');
      expect(get(detecting)).toBe(true);

      const notDetecting = useIsDetecting('eth', '0xaddr2');
      expect(get(notDetecting)).toBe(false);
    });

    it('should check across multiple chains', async () => {
      mockIsTaskRunning.mockImplementation((_type: unknown, meta: { chain: string }): boolean =>
        meta.chain === 'optimism',
      );

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { useIsDetecting } = useTokenDetectionOrchestrator();

      const detecting = useIsDetecting(['eth', 'optimism']);
      expect(get(detecting)).toBe(true);
    });
  });
});
