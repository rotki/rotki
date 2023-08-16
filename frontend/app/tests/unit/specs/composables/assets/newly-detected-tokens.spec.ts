import { expect } from 'vitest';
import flushPromises from 'flush-promises';

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
    composable.initTokens('test');
  });

  beforeEach(() => {
    composable.clearInternalTokens();
    set(ignoredAssets, []);
  });

  test('ignored tokens get removed from newly detected tokens', async () => {
    expect(
      composable.addNewDetectedToken({
        tokenIdentifier: '1234'
      })
    ).toBe(true);

    expect(get(composable.tokens)).toEqual([{ tokenIdentifier: '1234' }]);
    expect(get(ignoredAssets)).toStrictEqual([]);

    store.addIgnoredAsset('1234');

    expect(get(ignoredAssets)).toStrictEqual(['1234']);
    await flushPromises();
    expect(get(composable.tokens)).toStrictEqual([]);
  });

  test('ignored tokens are automatically added to the ignore list', async () => {
    expect(
      composable.addNewDetectedToken({
        tokenIdentifier: '1234',
        isIgnored: true
      })
    ).toBe(false);

    expect(get(ignoredAssets)).toMatchObject(['1234']);
  });
});
