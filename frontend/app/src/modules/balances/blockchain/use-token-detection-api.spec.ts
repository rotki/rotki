import type { EvmTokensRecord } from '@/modules/balances/types/balances';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

const mockSetState = vi.fn();
vi.mock('@/modules/balances/blockchain/use-token-detection-store', () => ({
  useTokenDetectionStore: vi.fn().mockReturnValue({
    setState: mockSetState,
  }),
}));

const mockFetchDetectedTokens = vi.fn();
const mockFetchDetectedTokensTask = vi.fn();
vi.mock('@/modules/balances/api/use-blockchain-balances-api', () => ({
  useBlockchainBalancesApi: vi.fn().mockReturnValue({
    fetchDetectedTokens: mockFetchDetectedTokens,
    fetchDetectedTokensTask: mockFetchDetectedTokensTask,
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    getChainName: (chain: string): string => chain.toUpperCase(),
  }),
}));

const mockRunTask = vi.fn();
vi.mock('@/modules/core/tasks/use-task-handler', () => ({
  useTaskHandler: vi.fn().mockReturnValue({
    runTask: mockRunTask,
  }),
  isActionableFailure: (outcome: { success: boolean; cancelled?: boolean; skipped?: boolean }): boolean =>
    !outcome.success && !outcome.cancelled && !outcome.skipped,
}));

const mockNotifyError = vi.fn();
vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn().mockReturnValue({
    notifyError: mockNotifyError,
  }),
  getErrorMessage: (e: unknown): string => (e instanceof Error ? e.message : String(e)),
}));

describe('useTokenDetectionApi', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('should fetch cached tokens when address is null', async () => {
    const cachedResult: EvmTokensRecord = {
      '0xaddr1': { lastUpdateTimestamp: 1000, tokens: ['DAI'] },
    };
    mockFetchDetectedTokens.mockResolvedValue(cachedResult);

    const { useTokenDetectionApi } = await import('./use-token-detection-api');
    const { fetchDetectedTokens } = useTokenDetectionApi();

    await fetchDetectedTokens('eth');

    expect(mockFetchDetectedTokens).toHaveBeenCalledWith('eth', null);
    expect(mockSetState).toHaveBeenCalledWith('eth', cachedResult);
    expect(mockRunTask).not.toHaveBeenCalled();
  });

  it('should run a task when address is provided', async () => {
    const taskResult: EvmTokensRecord = {
      '0xaddr1': { lastUpdateTimestamp: 2000, tokens: ['USDC'] },
    };
    mockRunTask.mockResolvedValue({ success: true, result: taskResult });

    const { useTokenDetectionApi } = await import('./use-token-detection-api');
    const { fetchDetectedTokens } = useTokenDetectionApi();

    await fetchDetectedTokens('eth', '0xaddr1');

    expect(mockRunTask).toHaveBeenCalledOnce();
    expect(mockSetState).toHaveBeenCalledWith('eth', taskResult);
  });

  it('should notify on task failure', async () => {
    mockRunTask.mockResolvedValue({
      success: false,
      cancelled: false,
      skipped: false,
      message: 'Network error',
      error: new Error('Network error'),
    });

    const { useTokenDetectionApi } = await import('./use-token-detection-api');
    const { fetchDetectedTokens } = useTokenDetectionApi();

    await fetchDetectedTokens('eth', '0xaddr1');

    expect(mockSetState).not.toHaveBeenCalled();
    expect(mockNotifyError).toHaveBeenCalledOnce();
  });

  it('should not notify on cancelled task', async () => {
    mockRunTask.mockResolvedValue({
      success: false,
      cancelled: true,
      skipped: false,
    });

    const { useTokenDetectionApi } = await import('./use-token-detection-api');
    const { fetchDetectedTokens } = useTokenDetectionApi();

    await fetchDetectedTokens('eth', '0xaddr1');

    expect(mockSetState).not.toHaveBeenCalled();
    expect(mockNotifyError).not.toHaveBeenCalled();
  });

  it('should notify on cached fetch error', async () => {
    mockFetchDetectedTokens.mockRejectedValue(new Error('API error'));

    const { useTokenDetectionApi } = await import('./use-token-detection-api');
    const { fetchDetectedTokens } = useTokenDetectionApi();

    await fetchDetectedTokens('eth');

    expect(mockSetState).not.toHaveBeenCalled();
    expect(mockNotifyError).toHaveBeenCalledOnce();
  });
});
