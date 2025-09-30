import flushPromises from 'flush-promises';
import { beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { useNewlyDetectedTokens } from '@/composables/assets/newly-detected-tokens';
import { NewDetectedTokenKind } from '@/modules/messaging/types';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';

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

  describe('eVM tokens', () => {
    it('ignored tokens get removed from newly detected tokens', async () => {
      expect(
        composable.addNewDetectedToken({
          tokenIdentifier: 'eip155:1/erc20:0x1234',
          tokenKind: NewDetectedTokenKind.EVM,
        }),
      ).toBe(true);

      expect(get(composable.tokens)).toEqual([{ tokenIdentifier: 'eip155:1/erc20:0x1234', tokenKind: NewDetectedTokenKind.EVM }]);
      expect(get(ignoredAssets)).toStrictEqual([]);

      store.addIgnoredAsset('eip155:1/erc20:0x1234');

      expect(get(ignoredAssets)).toStrictEqual(['eip155:1/erc20:0x1234']);
      await flushPromises();
      expect(get(composable.tokens)).toStrictEqual([]);
    });

    it('ignored tokens are automatically added to the ignore list', () => {
      expect(
        composable.addNewDetectedToken({
          tokenIdentifier: 'eip155:1/erc20:0x1234',
          tokenKind: NewDetectedTokenKind.EVM,
          isIgnored: true,
        }),
      ).toBe(false);

      expect(get(ignoredAssets)).toMatchObject(['eip155:1/erc20:0x1234']);
    });
  });

  describe('solana tokens', () => {
    it('ignored tokens get removed from newly detected tokens', async () => {
      expect(
        composable.addNewDetectedToken({
          tokenIdentifier: 'solana/token:So11111111111111111111111111111111111111112',
          tokenKind: NewDetectedTokenKind.SOLANA,
        }),
      ).toBe(true);

      expect(get(composable.tokens)).toEqual([{ tokenIdentifier: 'solana/token:So11111111111111111111111111111111111111112', tokenKind: NewDetectedTokenKind.SOLANA }]);
      expect(get(ignoredAssets)).toStrictEqual([]);

      store.addIgnoredAsset('solana/token:So11111111111111111111111111111111111111112');

      expect(get(ignoredAssets)).toStrictEqual(['solana/token:So11111111111111111111111111111111111111112']);
      await flushPromises();
      expect(get(composable.tokens)).toStrictEqual([]);
    });

    it('ignored tokens are automatically added to the ignore list', () => {
      expect(
        composable.addNewDetectedToken({
          tokenIdentifier: 'solana/token:So11111111111111111111111111111111111111112',
          tokenKind: NewDetectedTokenKind.SOLANA,
          isIgnored: true,
        }),
      ).toBe(false);

      expect(get(ignoredAssets)).toMatchObject(['solana/token:So11111111111111111111111111111111111111112']);
    });
  });

  describe('mixed token types', () => {
    it('handles both EVM and Solana tokens simultaneously', async () => {
      expect(
        composable.addNewDetectedToken({
          tokenIdentifier: 'eip155:1/erc20:0x1234',
          tokenKind: NewDetectedTokenKind.EVM,
        }),
      ).toBe(true);

      expect(
        composable.addNewDetectedToken({
          tokenIdentifier: 'solana/token:So11111111111111111111111111111111111111112',
          tokenKind: NewDetectedTokenKind.SOLANA,
        }),
      ).toBe(true);

      expect(get(composable.tokens)).toHaveLength(2);
      expect(get(composable.tokens)).toContainEqual({ tokenIdentifier: 'eip155:1/erc20:0x1234', tokenKind: NewDetectedTokenKind.EVM });
      expect(get(composable.tokens)).toContainEqual({ tokenIdentifier: 'solana/token:So11111111111111111111111111111111111111112', tokenKind: NewDetectedTokenKind.SOLANA });

      // Ignore the EVM token
      store.addIgnoredAsset('eip155:1/erc20:0x1234');
      await flushPromises();

      expect(get(composable.tokens)).toHaveLength(1);
      expect(get(composable.tokens)).toEqual([{ tokenIdentifier: 'solana/token:So11111111111111111111111111111111111111112', tokenKind: NewDetectedTokenKind.SOLANA }]);
    });
  });
});
