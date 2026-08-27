import { type AssetBalanceWithPrice, bigNumberify } from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, type ComputedRef, type Ref } from 'vue';
import { useAssetDetail } from './use-asset-detail';

const PARENT = 'ETH';
const MEMBER = 'eip155:1/erc20:0xabc';

interface AssetInfoShape {
  collectionId?: string;
  isCustomAsset?: boolean;
  name?: string;
  symbol?: string;
}

const { assetInfo, balances, pushMock, retrievalOptions, routeQuery } = vi.hoisted(() => {
  const assetInfo: { current: AssetInfoShape | null } = { current: null };
  const balances: { current: AssetBalanceWithPrice[] } = { current: [] };
  /** The resolution options the page hands the retrieval composables on each call. */
  const retrievalOptions: { current?: ComputedRef<{ collectionParent: boolean }> } = {};
  const routeQuery: { current: Record<string, string> } = { current: {} };

  return { assetInfo, balances, pushMock: vi.fn(async (): Promise<void> => {}), retrievalOptions, routeQuery };
});

vi.mock('vue-router', () => ({
  useRoute: (): ComputedRef<{ query: Record<string, string> }> => computed(() => ({ query: routeQuery.current })),
  useRouter: (): { push: typeof pushMock } => ({ push: pushMock }),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', async () => {
  const { computed: computedFn } = await import('vue');
  return {
    useAssetInfoRetrieval: (): Record<string, unknown> => ({
      refetchAssetInfo: vi.fn(),
      useAssetContractInfo: (): ComputedRef<null> => computedFn(() => null),
      useAssetInfo: (_id: unknown, options: ComputedRef<{ collectionParent: boolean }>): ComputedRef<AssetInfoShape | null> => {
        retrievalOptions.current = options;
        return computedFn(() => assetInfo.current);
      },
    }),
  };
});

vi.mock('@/modules/balances/use-aggregated-balances', async () => {
  const { computed: computedFn } = await import('vue');
  return {
    useAggregatedBalances: (): { useBalances: () => ComputedRef<AssetBalanceWithPrice[]> } => ({
      useBalances: (): ComputedRef<AssetBalanceWithPrice[]> => computedFn(() => balances.current),
    }),
  };
});

vi.mock('@/modules/premium/use-premium', async () => {
  const { shallowRef } = await import('vue');
  return { usePremium: (): Ref<boolean> => shallowRef(false) };
});

vi.mock('@/pages/assets/use-asset-page-actions', async () => {
  const { shallowRef } = await import('vue');
  return {
    useAssetPageActions: (): Record<string, unknown> => ({
      loadingIgnore: shallowRef(false),
      loadingSpam: shallowRef(false),
      loadingWhitelist: shallowRef(false),
      toggleIgnoreAsset: vi.fn(),
      toggleSpam: vi.fn(),
      toggleWhitelistAsset: vi.fn(),
    }),
  };
});

function balance(asset: string): AssetBalanceWithPrice {
  return {
    amount: bigNumberify(1),
    asset,
    price: bigNumberify(2),
    value: bigNumberify(2),
  };
}

describe('pages/assets/useAssetDetail', () => {
  function setup(identifier = PARENT): ReturnType<typeof useAssetDetail> {
    return withSetup(() => useAssetDetail(() => identifier)).result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    assetInfo.current = null;
    balances.current = [];
    routeQuery.current = {};
  });

  describe('the collectionParent query', () => {
    it('should read as a single asset when the query is absent', () => {
      const { isCollectionParent } = setup();

      expect(get(isCollectionParent)).toBe(false);
    });

    it('should read as a collection parent whatever value the query carries', () => {
      routeQuery.current = { collectionParent: 'false' };

      const { isCollectionParent } = setup();

      // Only the presence of the param is read; a literal "false" still means collection parent.
      expect(get(isCollectionParent)).toBe(true);
    });

    it('should pass the flag through to the asset resolution', () => {
      routeQuery.current = { collectionParent: 'true' };

      setup();

      expect(retrievalOptions.current?.value).toEqual({ collectionParent: true });
    });
  });

  describe('collectionId', () => {
    it('should be undefined for a single asset even when the asset names a collection', () => {
      assetInfo.current = { collectionId: '5' };

      const { collectionId } = setup();

      expect(get(collectionId)).toBeUndefined();
    });

    it('should parse the collection id for a parent', () => {
      routeQuery.current = { collectionParent: 'true' };
      assetInfo.current = { collectionId: '5' };

      const { collectionId } = setup();

      expect(get(collectionId)).toBe(5);
    });

    it('should be undefined when the parent names no collection', () => {
      routeQuery.current = { collectionParent: 'true' };
      assetInfo.current = {};

      const { collectionId } = setup();

      expect(get(collectionId)).toBeUndefined();
    });

    it('should treat a zero collection id as absent', () => {
      routeQuery.current = { collectionParent: 'true' };
      assetInfo.current = { collectionId: '0' };

      const { collectionId } = setup();

      expect(get(collectionId)).toBeUndefined();
    });
  });

  describe('collectionBalance', () => {
    it('should be empty for a single asset, whatever the balances hold', () => {
      balances.current = [{ ...balance(PARENT), breakdown: [balance(MEMBER)] }];

      const { collectionBalance } = setup();

      expect(get(collectionBalance)).toEqual([]);
    });

    it('should be the parent breakdown for a collection parent', () => {
      routeQuery.current = { collectionParent: 'true' };
      balances.current = [{ ...balance(PARENT), breakdown: [balance(MEMBER)] }];

      const { collectionBalance } = setup();

      expect(get(collectionBalance)).toHaveLength(1);
      expect(get(collectionBalance)[0].asset).toBe(MEMBER);
    });

    it('should be empty when the parent has no entry in the balances', () => {
      routeQuery.current = { collectionParent: 'true' };
      balances.current = [balance('BTC')];

      const { collectionBalance } = setup();

      expect(get(collectionBalance)).toEqual([]);
    });

    it('should be empty when the parent entry carries no breakdown', () => {
      routeQuery.current = { collectionParent: 'true' };
      balances.current = [balance(PARENT)];

      const { collectionBalance } = setup();

      expect(get(collectionBalance)).toEqual([]);
    });
  });

  describe('which asset the price chart follows', () => {
    it('should follow the asset itself when there is no collection', () => {
      const { collectionAssetWithPrice } = setup();

      expect(get(collectionAssetWithPrice)).toBe(PARENT);
    });

    it('should follow the parent when the parent is itself priced', () => {
      routeQuery.current = { collectionParent: 'true' };
      balances.current = [{ ...balance(PARENT), breakdown: [balance(MEMBER), balance(PARENT)] }];

      const { collectionAssetWithPrice } = setup();

      expect(get(collectionAssetWithPrice)).toBe(PARENT);
    });

    it('should fall back to the first member when the parent is not priced', () => {
      routeQuery.current = { collectionParent: 'true' };
      balances.current = [{ ...balance(PARENT), breakdown: [balance(MEMBER), balance('OTHER')] }];

      const { collectionAssetWithPrice } = setup();

      expect(get(collectionAssetWithPrice)).toBe(MEMBER);
    });
  });

  describe('the edit route', () => {
    it('should go to the managed asset manager for a regular asset', () => {
      assetInfo.current = { isCustomAsset: false };

      setup().goToEdit();

      expect(pushMock).toHaveBeenCalledWith({ path: '/asset-manager/managed', query: { id: PARENT } });
    });

    it('should go to the custom asset manager for a custom asset', () => {
      assetInfo.current = { isCustomAsset: true };

      setup().goToEdit();

      expect(pushMock).toHaveBeenCalledWith({ path: '/asset-manager/custom', query: { id: PARENT } });
    });
  });

  it('should report whether the asset is a custom one', () => {
    assetInfo.current = { isCustomAsset: true };

    expect(get(setup().isCustomAsset)).toBe(true);
  });
});
