import { flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// Note: This test suite tests the useAssetSelectInfo composable which uses createSharedComposable.
// Due to the shared nature of the composable (state persists across all instances),
// some tests may exhibit behavior influenced by previous test runs.
// The composable is designed to share cached data efficiently in production.

describe('composables/assets/asset-select-info', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Set up Pinia for the tests
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('basic functionality', () => {
    it('should return null when identifier is undefined', async () => {
      const { useAssetSelectInfo } = await import('@/composables/assets/asset-select-info');
      const assetSelectInfo = useAssetSelectInfo();

      const result = assetSelectInfo.assetInfo(undefined);
      expect(get(result)).toBeNull();
    });

    it('should return null when identifier is empty string', async () => {
      const { useAssetSelectInfo } = await import('@/composables/assets/asset-select-info');
      const assetSelectInfo = useAssetSelectInfo();

      const result = assetSelectInfo.assetInfo('');
      expect(get(result)).toBeNull();
    });

    it('should return empty string for symbol when identifier is undefined', async () => {
      const { useAssetSelectInfo } = await import('@/composables/assets/asset-select-info');
      const assetSelectInfo = useAssetSelectInfo();

      const result = assetSelectInfo.assetSymbol(undefined);
      expect(get(result)).toBe('');
    });

    it('should return empty string for symbol when identifier is empty', async () => {
      const { useAssetSelectInfo } = await import('@/composables/assets/asset-select-info');
      const assetSelectInfo = useAssetSelectInfo();

      const result = assetSelectInfo.assetSymbol('');
      expect(get(result)).toBe('');
    });

    it('should return empty string for name when identifier is undefined', async () => {
      const { useAssetSelectInfo } = await import('@/composables/assets/asset-select-info');
      const assetSelectInfo = useAssetSelectInfo();

      const result = assetSelectInfo.assetName(undefined);
      expect(get(result)).toBe('');
    });

    it('should return empty string for name when identifier is empty', async () => {
      const { useAssetSelectInfo } = await import('@/composables/assets/asset-select-info');
      const assetSelectInfo = useAssetSelectInfo();

      const result = assetSelectInfo.assetName('');
      expect(get(result)).toBe('');
    });
  });

  describe('reactive behavior', () => {
    it('should handle reactive identifier changes', async () => {
      const { useAssetSelectInfo } = await import('@/composables/assets/asset-select-info');
      const assetSelectInfo = useAssetSelectInfo();

      const identifier = ref<string | undefined>(undefined);
      const nameResult = assetSelectInfo.assetName(identifier);
      const symbolResult = assetSelectInfo.assetSymbol(identifier);
      const infoResult = assetSelectInfo.assetInfo(identifier);

      // Initially all return default values for undefined
      expect(get(nameResult)).toBe('');
      expect(get(symbolResult)).toBe('');
      expect(get(infoResult)).toBeNull();

      // Change to empty string
      set(identifier, '');

      // Should still return default values
      expect(get(nameResult)).toBe('');
      expect(get(symbolResult)).toBe('');
      expect(get(infoResult)).toBeNull();

      // Change back to undefined
      set(identifier, undefined);

      expect(get(nameResult)).toBe('');
      expect(get(symbolResult)).toBe('');
      expect(get(infoResult)).toBeNull();
    });
  });

  describe('error handling', () => {
    it('should handle undefined mapping response gracefully', async () => {
      const { useAssetSelectInfo } = await import('@/composables/assets/asset-select-info');
      const { useAssetInfoApi } = await import('@/composables/api/assets/info');

      const assetSelectInfo = useAssetSelectInfo();

      // Mock the API to return undefined
      const mockAssetMapping = vi.fn().mockResolvedValue(undefined);
      vi.mocked(useAssetInfoApi).mockReturnValue({
        assetMapping: mockAssetMapping,
        assetSearch: vi.fn(),
        erc20details: vi.fn(),
      });

      const undefinedId = `UNDEFINED_TEST_${Date.now()}`;
      const result = assetSelectInfo.assetInfo(undefinedId);

      // Initially null
      expect(get(result)).toBeNull();

      // Process the debounced request
      await vi.advanceTimersByTimeAsync(1600);
      await flushPromises();

      // Should still be null after processing
      expect(get(result)).toBeNull();
    });
  });

  describe('shared composable behavior', () => {
    it('should share the same instance between multiple calls', async () => {
      const { useAssetSelectInfo } = await import('@/composables/assets/asset-select-info');

      const instance1 = useAssetSelectInfo();
      const instance2 = useAssetSelectInfo();

      // Both instances should be the same due to createSharedComposable
      expect(instance1).toBe(instance2);
    });
  });
});
