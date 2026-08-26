import type { EffectScope } from 'vue';
import { flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MAX_PARALLEL_ASSET_BATCHES } from '@/modules/assets/use-asset-select-info';

// Note: This test suite tests the useAssetSelectInfo composable which uses createSharedComposable.
// Due to the shared nature of the composable (state persists across all instances),
// some tests may exhibit behavior influenced by previous test runs.
// The composable is designed to share cached data efficiently in production.

/** Comfortably past the composable's 200ms batch debounce, so a queued batch has been sent. */
const PAST_DEBOUNCE_MS = 300;

/** Several debounce intervals, long enough for a retry loop to show itself if one exists. */
const SEVERAL_DEBOUNCES_MS = 3000;

describe('useAssetSelectInfo', () => {
  let scope: EffectScope;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    setActivePinia(createPinia());
    scope = effectScope();
  });

  afterEach(() => {
    scope.stop();
    vi.useRealTimers();
  });

  describe('basic functionality', () => {
    it('should return null when identifier is undefined', async () => {
      const { useAssetSelectInfo } = await import('@/modules/assets/use-asset-select-info');
      const assetSelectInfo = scope.run(() => useAssetSelectInfo())!;

      const result = assetSelectInfo.getAssetInfo(undefined);
      expect(result).toBeNull();
    });

    it('should return null when identifier is empty string', async () => {
      const { useAssetSelectInfo } = await import('@/modules/assets/use-asset-select-info');
      const assetSelectInfo = scope.run(() => useAssetSelectInfo())!;

      const result = assetSelectInfo.getAssetInfo('');
      expect(result).toBeNull();
    });

    it('should return empty string for symbol when identifier is undefined', async () => {
      const { useAssetSelectInfo } = await import('@/modules/assets/use-asset-select-info');
      const assetSelectInfo = scope.run(() => useAssetSelectInfo())!;

      const result = assetSelectInfo.getAssetField(undefined, 'symbol');
      expect(result).toBe('');
    });

    it('should return empty string for symbol when identifier is empty', async () => {
      const { useAssetSelectInfo } = await import('@/modules/assets/use-asset-select-info');
      const assetSelectInfo = scope.run(() => useAssetSelectInfo())!;

      const result = assetSelectInfo.getAssetField('', 'symbol');
      expect(result).toBe('');
    });

    it('should return empty string for name when identifier is undefined', async () => {
      const { useAssetSelectInfo } = await import('@/modules/assets/use-asset-select-info');
      const assetSelectInfo = scope.run(() => useAssetSelectInfo())!;

      const result = assetSelectInfo.getAssetField(undefined, 'name');
      expect(result).toBe('');
    });

    it('should return empty string for name when identifier is empty', async () => {
      const { useAssetSelectInfo } = await import('@/modules/assets/use-asset-select-info');
      const assetSelectInfo = scope.run(() => useAssetSelectInfo())!;

      const result = assetSelectInfo.getAssetField('', 'name');
      expect(result).toBe('');
    });
  });

  describe('reactive behavior', () => {
    it('should keep returning defaults as the identifier moves between undefined and empty', async () => {
      const { useAssetSelectInfo } = await import('@/modules/assets/use-asset-select-info');
      const assetSelectInfo = scope.run(() => useAssetSelectInfo())!;

      const identifier = ref<string | undefined>(undefined);
      const nameResult = assetSelectInfo.useAssetField(identifier, 'name');
      const symbolResult = assetSelectInfo.useAssetField(identifier, 'symbol');
      const infoResult = assetSelectInfo.useAssetInfo(identifier);

      const expectDefaults = (): void => {
        expect(get(nameResult)).toBe('');
        expect(get(symbolResult)).toBe('');
        expect(get(infoResult)).toBeNull();
      };

      expectDefaults();

      set(identifier, '');
      expectDefaults();

      set(identifier, undefined);
      expectDefaults();
    });
  });

  describe('error handling', () => {
    it('should handle undefined mapping response gracefully', async () => {
      const { useAssetSelectInfo } = await import('@/modules/assets/use-asset-select-info');
      const { useAssetInfoApi } = await import('@/modules/assets/api/use-asset-info-api');

      const assetSelectInfo = scope.run(() => useAssetSelectInfo())!;

      const mockAssetMapping = vi.fn().mockResolvedValue(undefined);
      vi.mocked(useAssetInfoApi).mockReturnValue({
        assetMapping: mockAssetMapping,
        assetSearch: vi.fn(),
        erc20details: vi.fn(),
      });

      const undefinedId = `UNDEFINED_TEST_${Date.now()}`;
      const result = assetSelectInfo.useAssetInfo(undefinedId);

      expect(get(result)).toBeNull();

      await vi.advanceTimersByTimeAsync(PAST_DEBOUNCE_MS);
      await flushPromises();

      expect(get(result)).toBeNull();
    });
  });

  describe('prefetching', () => {
    it('should resolve identifiers that nothing has rendered, in one request', async () => {
      const { useAssetSelectInfo } = await import('@/modules/assets/use-asset-select-info');
      const { useAssetInfoApi } = await import('@/modules/assets/api/use-asset-info-api');

      const assetMapping = vi.fn().mockResolvedValue({
        assetCollections: {},
        assets: {
          PREFETCH_ONE: { name: 'Prefetch One', symbol: 'PF1' },
          PREFETCH_TWO: { name: 'Prefetch Two', symbol: 'PF2' },
        },
      });
      vi.mocked(useAssetInfoApi).mockReturnValue({
        assetMapping,
        assetSearch: vi.fn(),
        erc20details: vi.fn(),
      });

      const assetSelectInfo = scope.run(() => useAssetSelectInfo())!;
      assetSelectInfo.prefetchAssetInfo(['PREFETCH_ONE', 'PREFETCH_TWO']);

      await vi.advanceTimersByTimeAsync(PAST_DEBOUNCE_MS);
      await flushPromises();

      expect(assetMapping).toHaveBeenCalledTimes(1);
      expect(assetMapping).toHaveBeenCalledWith(['PREFETCH_ONE', 'PREFETCH_TWO']);
      expect(assetSelectInfo.getAssetInfo('PREFETCH_ONE')?.symbol).toBe('PF1');
      expect(assetSelectInfo.getAssetInfo('PREFETCH_TWO')?.symbol).toBe('PF2');
    });

    it('should send the batches of a large prefetch in parallel', async () => {
      const { useAssetSelectInfo } = await import('@/modules/assets/use-asset-select-info');
      const { useAssetInfoApi } = await import('@/modules/assets/api/use-asset-info-api');

      let inFlight = 0;
      let peakInFlight = 0;
      const releases: Array<() => void> = [];
      const assetMapping = vi.fn(async () => {
        inFlight += 1;
        peakInFlight = Math.max(peakInFlight, inFlight);
        await new Promise<void>((resolve) => {
          releases.push(resolve);
        });
        inFlight -= 1;
        return { assetCollections: {}, assets: {} };
      });
      vi.mocked(useAssetInfoApi).mockReturnValue({
        assetMapping,
        assetSearch: vi.fn(),
        erc20details: vi.fn(),
      });

      const assetSelectInfo = scope.run(() => useAssetSelectInfo())!;
      assetSelectInfo.prefetchAssetInfo(Array.from({ length: 120 }, (_, index) => `PARALLEL_${index}`));

      // Every batch is started before any of them is allowed to resolve, so the peak is the number
      // of batches only if they were sent together.
      await vi.advanceTimersByTimeAsync(PAST_DEBOUNCE_MS);
      expect(peakInFlight).toBe(3);

      releases.forEach(release => release());
      await flushPromises();

      expect(assetMapping).toHaveBeenCalledTimes(3);
    });

    it('should cap how many batches are in flight at once', async () => {
      const { useAssetSelectInfo } = await import('@/modules/assets/use-asset-select-info');
      const { useAssetInfoApi } = await import('@/modules/assets/api/use-asset-info-api');

      let inFlight = 0;
      let peakInFlight = 0;
      const releases: Array<() => void> = [];
      const assetMapping = vi.fn(async () => {
        inFlight += 1;
        peakInFlight = Math.max(peakInFlight, inFlight);
        await new Promise<void>((resolve) => {
          releases.push(resolve);
        });
        inFlight -= 1;
        return { assetCollections: {}, assets: {} };
      });
      vi.mocked(useAssetInfoApi).mockReturnValue({
        assetMapping,
        assetSearch: vi.fn(),
        erc20details: vi.fn(),
      });

      const assetSelectInfo = scope.run(() => useAssetSelectInfo())!;
      // 20 batches worth, far past the cap.
      assetSelectInfo.prefetchAssetInfo(Array.from({ length: 1000 }, (_, index) => `CAPPED_${index}`));

      await vi.advanceTimersByTimeAsync(PAST_DEBOUNCE_MS);
      expect(peakInFlight).toBeLessThanOrEqual(MAX_PARALLEL_ASSET_BATCHES);
      expect(peakInFlight).toBe(MAX_PARALLEL_ASSET_BATCHES);

      releases.forEach(release => release());
      await flushPromises();
    });

    it('should not retry in a loop when the mapping endpoint keeps failing', async () => {
      const { useAssetSelectInfo } = await import('@/modules/assets/use-asset-select-info');
      const { useAssetInfoApi } = await import('@/modules/assets/api/use-asset-info-api');

      const assetMapping = vi.fn().mockRejectedValue(new Error('boom'));
      vi.mocked(useAssetInfoApi).mockReturnValue({
        assetMapping,
        assetSearch: vi.fn(),
        erc20details: vi.fn(),
      });

      const assetSelectInfo = scope.run(() => useAssetSelectInfo())!;
      // A computed standing in for the table: it re-reads whenever the cache ref is replaced.
      const info = scope.run(() => assetSelectInfo.useAssetInfo('FAILING_ONE'))!;
      expect(get(info)).toBeNull();

      await vi.advanceTimersByTimeAsync(PAST_DEBOUNCE_MS);
      await flushPromises();
      const afterFirstAttempt = assetMapping.mock.calls.length;
      expect(afterFirstAttempt).toBe(1);

      // A failed batch must not replace the cache ref: that wakes every reader, which re-queues the
      // same identifiers, which fails again, at the debounce interval, for as long as the table is
      // on screen.
      get(info);
      await vi.advanceTimersByTimeAsync(SEVERAL_DEBOUNCES_MS);
      await flushPromises();
      expect(assetMapping).toHaveBeenCalledTimes(afterFirstAttempt);
    });

    it('should not re-request an identifier that is already cached', async () => {
      const { useAssetSelectInfo } = await import('@/modules/assets/use-asset-select-info');
      const { useAssetInfoApi } = await import('@/modules/assets/api/use-asset-info-api');

      const assetMapping = vi.fn().mockResolvedValue({
        assetCollections: {},
        assets: { CACHED_ONE: { name: 'Cached One', symbol: 'C1' } },
      });
      vi.mocked(useAssetInfoApi).mockReturnValue({
        assetMapping,
        assetSearch: vi.fn(),
        erc20details: vi.fn(),
      });

      const assetSelectInfo = scope.run(() => useAssetSelectInfo())!;
      assetSelectInfo.prefetchAssetInfo(['CACHED_ONE']);
      await vi.advanceTimersByTimeAsync(PAST_DEBOUNCE_MS);
      await flushPromises();

      assetSelectInfo.prefetchAssetInfo(['CACHED_ONE']);
      await vi.advanceTimersByTimeAsync(PAST_DEBOUNCE_MS);
      await flushPromises();

      expect(assetMapping).toHaveBeenCalledTimes(1);
    });
  });

  describe('shared composable behavior', () => {
    it('should share the same instance between multiple calls', async () => {
      const { useAssetSelectInfo } = await import('@/modules/assets/use-asset-select-info');

      const instance1 = scope.run(() => useAssetSelectInfo())!;
      const instance2 = scope.run(() => useAssetSelectInfo())!;

      // Both instances should be the same due to createSharedComposable
      expect(instance1).toBe(instance2);
    });
  });
});
