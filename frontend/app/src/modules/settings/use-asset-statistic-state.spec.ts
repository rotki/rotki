import { withSetup } from '@test/utils/with-setup';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetStatisticState } from './use-asset-statistic-state';

const storeEnabled = ref<boolean>(false);
const useAssetField = vi.fn((_asset?: unknown, _key?: unknown) => computed<string>(() => 'Bitcoin'));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn((key: string) => (key === 'useHistoricalAssetBalances' ? storeEnabled : ref(undefined))),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): object => ({
    useAssetField: (asset: unknown, key: unknown) => useAssetField(asset, key),
  }),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

describe('useAssetStatisticState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    set(storeEnabled, false);
  });

  it('should expose the asset name from the retrieval helper', () => {
    const { name } = withSetup(() => useAssetStatisticState(() => 'BTC')).result;
    expect(get(name)).toBe('Bitcoin');
  });

  it('should report no preference for an untracked asset', () => {
    const { getPreference, rememberStateForAsset } = withSetup(() => useAssetStatisticState(() => 'BTC')).result;
    expect(getPreference('BTC')).toBeUndefined();
    expect(get(rememberStateForAsset)).toBe(false);
  });

  it('should store the snapshot preference when remembering with historical disabled', () => {
    const { getPreference, rememberStateForAsset } = withSetup(() => useAssetStatisticState(() => 'BTC')).result;
    set(rememberStateForAsset, true);
    expect(get(rememberStateForAsset)).toBe(true);
    expect(getPreference('BTC')).toBe('snapshot');
  });

  it('should store the events preference when remembering with historical enabled', () => {
    const { getPreference, rememberStateForAsset, useHistoricalAssetBalances } = withSetup(() => useAssetStatisticState(() => 'BTC')).result;
    set(useHistoricalAssetBalances, true);
    set(rememberStateForAsset, true);
    expect(getPreference('BTC')).toBe('events');
  });

  it('should drop the preference when remembering is turned off', () => {
    const { getPreference, rememberStateForAsset } = withSetup(() => useAssetStatisticState(() => 'BTC')).result;
    set(rememberStateForAsset, true);
    expect(getPreference('BTC')).toBe('snapshot');
    set(rememberStateForAsset, false);
    expect(getPreference('BTC')).toBeUndefined();
  });

  it('should skip the callback in suppressIfPerAsset when remembering per asset', async () => {
    const { rememberStateForAsset, suppressIfPerAsset } = withSetup(() => useAssetStatisticState(() => 'BTC')).result;
    set(rememberStateForAsset, true);
    const func = vi.fn().mockResolvedValue(undefined);
    await suppressIfPerAsset(func);
    expect(func).not.toHaveBeenCalled();
  });

  it('should run the callback in suppressIfPerAsset when not remembering per asset', async () => {
    const { suppressIfPerAsset } = withSetup(() => useAssetStatisticState(() => 'BTC')).result;
    const func = vi.fn().mockResolvedValue(undefined);
    await suppressIfPerAsset(func);
    expect(func).toHaveBeenCalledOnce();
  });
});
