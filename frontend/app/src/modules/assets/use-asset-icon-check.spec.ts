import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mockCheckAsset = vi.fn();

vi.mock('@/modules/assets/api/use-asset-icon-api', () => ({
  useAssetIconApi: vi.fn((): { checkAsset: typeof mockCheckAsset } => ({
    checkAsset: mockCheckAsset,
  })),
}));

vi.mock('@shared/utils', () => ({
  wait: vi.fn(async (): Promise<void> => Promise.resolve()),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: {
    debug: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

describe('modules/assets/use-asset-icon-check', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.resetModules();
    mockCheckAsset.mockReset();
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  async function createCheck(): Promise<{
    checkIfAssetExists: (id: string, opts: { abortController?: AbortController }) => Promise<boolean>;
    clearIconCache: () => void;
    setLastRefreshedAssetIcon: () => void;
  }> {
    const { useAssetIconCheck } = await import('./use-asset-icon-check');
    const { useAssetsStore } = await import('./use-assets-store');
    const store = useAssetsStore();
    const { checkIfAssetExists } = useAssetIconCheck();
    return {
      checkIfAssetExists,
      clearIconCache: store.clearIconCache,
      setLastRefreshedAssetIcon: store.setLastRefreshedAssetIcon,
    };
  }

  it('should return cached result when within TTL', async () => {
    const { checkIfAssetExists } = await createCheck();

    mockCheckAsset.mockResolvedValueOnce(200);
    const result1 = await checkIfAssetExists('ETH', {});
    expect(result1).toBe(true);
    expect(mockCheckAsset).toHaveBeenCalledTimes(1);

    const result2 = await checkIfAssetExists('ETH', {});
    expect(result2).toBe(true);
    expect(mockCheckAsset).toHaveBeenCalledTimes(1);
  });

  it('should fetch again when cache TTL expires', async () => {
    const { checkIfAssetExists } = await createCheck();

    mockCheckAsset.mockResolvedValueOnce(200);
    await checkIfAssetExists('ETH', {});
    expect(mockCheckAsset).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(5 * 60 * 1000 + 1);

    mockCheckAsset.mockResolvedValueOnce(200);
    await checkIfAssetExists('ETH', {});
    expect(mockCheckAsset).toHaveBeenCalledTimes(2);
  });

  it('should deduplicate concurrent requests for the same identifier', async () => {
    const { checkIfAssetExists } = await createCheck();

    let resolveCheck: (value: number) => void;
    const checkPromise = new Promise<number>((resolve) => {
      resolveCheck = resolve;
    });
    mockCheckAsset.mockReturnValueOnce(checkPromise);

    const request1 = checkIfAssetExists('ETH', {});
    const request2 = checkIfAssetExists('ETH', {});

    resolveCheck!(200);

    const [result1, result2] = await Promise.all([request1, request2]);
    expect(result1).toBe(true);
    expect(result2).toBe(true);
    expect(mockCheckAsset).toHaveBeenCalledTimes(1);
  });

  it('should cache true for 200 response', async () => {
    const { checkIfAssetExists } = await createCheck();

    mockCheckAsset.mockResolvedValueOnce(200);
    const result = await checkIfAssetExists('ETH', {});
    expect(result).toBe(true);

    const result2 = await checkIfAssetExists('ETH', {});
    expect(result2).toBe(true);
    expect(mockCheckAsset).toHaveBeenCalledTimes(1);
  });

  it('should cache false for 404 response', async () => {
    const { checkIfAssetExists } = await createCheck();

    mockCheckAsset.mockResolvedValueOnce(404);
    const result = await checkIfAssetExists('UNKNOWN', {});
    expect(result).toBe(false);

    const result2 = await checkIfAssetExists('UNKNOWN', {});
    expect(result2).toBe(false);
    expect(mockCheckAsset).toHaveBeenCalledTimes(1);
  });

  it('should handle different identifiers separately', async () => {
    const { checkIfAssetExists } = await createCheck();

    mockCheckAsset.mockResolvedValueOnce(200);
    mockCheckAsset.mockResolvedValueOnce(404);

    const result1 = await checkIfAssetExists('ETH', {});
    const result2 = await checkIfAssetExists('BTC', {});

    expect(result1).toBe(true);
    expect(result2).toBe(false);
    expect(mockCheckAsset).toHaveBeenCalledTimes(2);
  });

  it('should remove pending request after completion', async () => {
    const { checkIfAssetExists } = await createCheck();

    mockCheckAsset.mockResolvedValueOnce(200);
    await checkIfAssetExists('ETH', {});

    vi.advanceTimersByTime(5 * 60 * 1000 + 1);

    mockCheckAsset.mockResolvedValueOnce(200);
    await checkIfAssetExists('ETH', {});

    expect(mockCheckAsset).toHaveBeenCalledTimes(2);
  });

  it('should return false when request is aborted', async () => {
    const { checkIfAssetExists } = await createCheck();

    const abortController = new AbortController();
    mockCheckAsset.mockResolvedValue(500);

    const requestPromise = checkIfAssetExists('ETH', { abortController });
    abortController.abort();

    const result = await requestPromise;
    expect(result).toBe(false);
  });

  it('should return false on error', async () => {
    const { checkIfAssetExists } = await createCheck();

    mockCheckAsset.mockRejectedValueOnce(new Error('Network error'));

    const result = await checkIfAssetExists('ETH', {});
    expect(result).toBe(false);
  });

  it('should clear cache when lastRefreshed changes', async () => {
    const { checkIfAssetExists, setLastRefreshedAssetIcon } = await createCheck();

    mockCheckAsset.mockResolvedValueOnce(200);
    await checkIfAssetExists('ETH', {});
    expect(mockCheckAsset).toHaveBeenCalledTimes(1);

    setLastRefreshedAssetIcon();
    await nextTick();

    mockCheckAsset.mockResolvedValueOnce(200);
    await checkIfAssetExists('ETH', {});
    expect(mockCheckAsset).toHaveBeenCalledTimes(2);
  });
});
