import { useNewlyDetectedTokens } from '@/composables/assets/newly-detected-tokens';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import flushPromises from 'flush-promises';
import { beforeAll, beforeEach, describe, expect, it } from 'vitest';

describe('composables::/assets/newly-detected-tokens', () => {
  let composable: ReturnType<typeof useNewlyDetectedTokens>;
  let store: ReturnType<typeof useIgnoredAssetsStore>;
  let ignoredAssets: Ref<string[]>;

  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    store = useIgnoredAssetsStore();
    ignoredAssets = storeToRefs(store).ignoredAssets;
    composable = useNewlyDetectedTokens();
  });

  beforeEach(() => {
    composable.clearInternalTokens();
    set(ignoredAssets, []);
  });

  it('ignored tokens get removed from newly detected tokens', async () => {
    expect(
      composable.addNewDetectedToken({
        tokenIdentifier: '1234',
      }),
    ).toBe(true);

    expect(get(composable.tokens)).toEqual([{ tokenIdentifier: '1234' }]);
    expect(get(ignoredAssets)).toStrictEqual([]);

    store.addIgnoredAsset('1234');

    expect(get(ignoredAssets)).toStrictEqual(['1234']);
    await flushPromises();
    expect(get(composable.tokens)).toStrictEqual([]);
  });

  it('ignored tokens are automatically added to the ignore list', () => {
    expect(
      composable.addNewDetectedToken({
        tokenIdentifier: '1234',
        isIgnored: true,
      }),
    ).toBe(false);

    expect(get(ignoredAssets)).toMatchObject(['1234']);
  });
});
