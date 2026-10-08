import type { EvmTokensRecord } from '@/modules/balances/types/balances';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
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

const mockRunTask = vi.fn();

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
    const { fetchCachedDetectedTokens } = useTokenDetectionApi();

    await fetchCachedDetectedTokens('eth');

    expect(mockFetchDetectedTokens).toHaveBeenCalledWith('eth', null);
    expect(mockSetState).toHaveBeenCalledWith('eth', cachedResult);
    expect(mockRunTask).not.toHaveBeenCalled();
  });

  it('should run a task when address is provided', async () => {
    const taskResult: EvmTokensRecord = {
      '0xaddr1': { lastUpdateTimestamp: 2000, tokens: ['USDC'] },
    };
    mockRunTask.mockResolvedValue(ok(taskResult));

    const { useTokenDetectionApi } = await import('./use-token-detection-api');
    const { detectTokensForAddress } = useTokenDetectionApi();

    await detectTokensForAddress(mockRunTask, 'eth', '0xaddr1');

    expect(mockRunTask).toHaveBeenCalledOnce();
    expect(mockSetState).toHaveBeenCalledWith('eth', taskResult);
  });

  it('should hand a failed detection back to its activity, whose dock row reports it', async () => {
    mockRunTask.mockResolvedValue(err(TaskFailed({ message: 'Network error' })));

    const { useTokenDetectionApi } = await import('./use-token-detection-api');
    const { detectTokensForAddress } = useTokenDetectionApi();

    const result = await detectTokensForAddress(mockRunTask, 'eth', '0xaddr1');

    expect(result).toEqual(err(TaskFailed({ message: 'Network error' })));
    expect(mockSetState).not.toHaveBeenCalled();
  });

  it('should hand a cancelled detection back as a cancellation', async () => {
    mockRunTask.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

    const { useTokenDetectionApi } = await import('./use-token-detection-api');
    const { detectTokensForAddress } = useTokenDetectionApi();

    const result = await detectTokensForAddress(mockRunTask, 'eth', '0xaddr1');

    expect(result).toEqual(err(Cancelled({ message: 'cancelled' })));
    expect(mockSetState).not.toHaveBeenCalled();
  });

  it('should return a failed cached read with its reason and keep the previous state', async () => {
    mockFetchDetectedTokens.mockRejectedValue(new Error('API error'));

    const { useTokenDetectionApi } = await import('./use-token-detection-api');
    const { fetchCachedDetectedTokens } = useTokenDetectionApi();

    const result = await fetchCachedDetectedTokens('eth');

    expect(result).toEqual(err(TaskFailed({ message: 'API error' })));
    expect(mockSetState).not.toHaveBeenCalled();
  });
});
