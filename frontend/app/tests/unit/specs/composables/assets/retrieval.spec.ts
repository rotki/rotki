import { type ERC20Token } from '@/types/blockchain/accounts';
import { CUSTOM_ASSET } from '@/types/asset';
import { updateGeneralSettings } from '../../../utils/general-settings';

vi.mock('@/composables/api/assets/info', () => ({
  useAssetInfoApi: vi.fn().mockReturnValue({
    erc20details: vi.fn().mockResolvedValue(1)
  })
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({})
  })
}));

vi.mock('@/store/notifications/index', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({
    notify: vi.fn().mockReturnValue({})
  })
}));

describe('store::assets/retrieval', () => {
  let assetInfoRetrieval: ReturnType<typeof useAssetInfoRetrieval>;
  let assetCacheStore: ReturnType<typeof useAssetCacheStore>;
  let api: ReturnType<typeof useAssetInfoApi>;

  beforeEach(() => {
    setActivePinia(createPinia());
    assetCacheStore = useAssetCacheStore();
    vi.spyOn(assetCacheStore, 'isPending');
    vi.spyOn(assetCacheStore, 'retrieve');
    assetInfoRetrieval = useAssetInfoRetrieval();
    api = useAssetInfoApi();
  });

  describe('getAssociatedAssetIdentifier', () => {
    test('ETH2 as ETH = true', () => {
      updateGeneralSettings({
        treatEth2AsEth: true
      });

      const result = get(
        assetInfoRetrieval.getAssociatedAssetIdentifier('ETH2')
      );

      expect(result).toEqual('ETH');
    });

    test('ETH2 as ETH = false', () => {
      updateGeneralSettings({
        treatEth2AsEth: false
      });

      const result = get(
        assetInfoRetrieval.getAssociatedAssetIdentifier('ETH2')
      );

      expect(result).toEqual('ETH2');
    });
  });

  describe('fetchTokenDetails', () => {
    const address = '0x12BB890508c125661E03b09EC06E404bc9289040';

    test('success', async () => {
      const tokenDetail: ERC20Token = {
        decimals: 18,
        name: 'Radio Caca',
        symbol: 'RACA'
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: tokenDetail,
        meta: { title: '' }
      });

      const result = await assetInfoRetrieval.fetchTokenDetails(address);

      expect(api.erc20details).toHaveBeenCalledWith(address);

      expect(result).toEqual(tokenDetail);

      expect(useNotificationsStore().notify).not.toHaveBeenCalled();
    });

    test('failed', async () => {
      vi.mocked(useTaskStore().awaitTask).mockRejectedValue(
        new Error('failed')
      );

      const result = await assetInfoRetrieval.fetchTokenDetails(address);

      expect(api.erc20details).toHaveBeenCalledWith(address);

      expect(result).toEqual({});

      expect(useNotificationsStore().notify).toHaveBeenCalled();
    });
  });

  describe('assetInfo, assetName, and assetSymbol', () => {
    test('identifier falsy', () => {
      const identifier = undefined;
      expect(get(assetInfoRetrieval.assetInfo(identifier))).toEqual(null);
      expect(get(assetInfoRetrieval.assetName(identifier))).toEqual('');
      expect(get(assetInfoRetrieval.assetName(identifier))).toEqual('');
    });

    test('asset cache for identifier is pending', async () => {
      const identifier = 'ETH';
      vi.mocked(assetCacheStore.isPending).mockReturnValue(
        computed(() => true)
      );

      expect(get(assetInfoRetrieval.assetInfo(identifier))).toEqual(null);
      expect(get(assetInfoRetrieval.assetName(identifier))).toEqual('');
      expect(get(assetInfoRetrieval.assetName(identifier))).toEqual('');
    });

    describe('custom asset', () => {
      const identifier = 'ASSET_ID';
      const assetName = 'ASSET_NAME';

      afterEach(() => {
        vi.mocked(assetCacheStore.retrieve).mockReturnValue(
          computed(() => ({
            name: assetName,
            isCustomAsset: true
          }))
        );

        const result = get(assetInfoRetrieval.assetInfo(identifier));

        expect(assetCacheStore.retrieve).toHaveBeenCalledWith(identifier);

        expect(result).toMatchObject({
          name: assetName,
          symbol: assetName,
          isCustomAsset: true
        });

        expect(get(assetInfoRetrieval.assetName(identifier))).toEqual(
          assetName
        );
        expect(get(assetInfoRetrieval.assetSymbol(identifier))).toEqual(
          assetName
        );
      });

      test('isCustomAsset = true', () => {
        vi.mocked(assetCacheStore.retrieve).mockReturnValue(
          computed(() => ({
            name: assetName,
            isCustomAsset: true
          }))
        );
      });

      test('assetType === CUSTOM_ASSET', () => {
        vi.mocked(assetCacheStore.retrieve).mockReturnValue(
          computed(() => ({
            name: assetName,
            assetType: CUSTOM_ASSET
          }))
        );
      });
    });

    describe('asset with collection parent', () => {
      const identifier = 'USDC_IN_OPTIMISM';
      const collectionId = '1';
      const assetName = 'USDC in Optimism';
      const assetSymbol = 'USDC';
      const collectionName = 'USDC Generic Name';

      beforeEach(() => {
        const { fetchedAssetCollections } = storeToRefs(assetCacheStore);

        set(fetchedAssetCollections, {
          [collectionId]: {
            name: collectionName,
            symbol: assetSymbol
          }
        });

        vi.mocked(assetCacheStore.retrieve).mockReturnValue(
          computed(() => ({
            name: assetName,
            symbol: assetSymbol,
            collectionId
          }))
        );
      });

      test('isCollectionParent = true', () => {
        const result = get(assetInfoRetrieval.assetInfo(identifier));

        expect(result).toMatchObject({
          name: collectionName,
          symbol: assetSymbol
        });

        expect(get(assetInfoRetrieval.assetName(identifier))).toEqual(
          collectionName
        );
        expect(get(assetInfoRetrieval.assetSymbol(identifier))).toEqual(
          assetSymbol
        );
      });

      test('isCollectionParent = false', () => {
        const result = get(
          assetInfoRetrieval.assetInfo(identifier, true, false)
        );

        expect(result).toMatchObject({
          name: assetName,
          symbol: assetSymbol
        });
      });
    });

    test('asset name and symbol using fallback', () => {
      const address = '0x12BB890508c125661E03b09EC06E404bc9289040';
      const identifier = `eip155:1/erc-20:${address}`;
      vi.mocked(assetCacheStore.retrieve).mockReturnValue(computed(() => null));

      const result = get(assetInfoRetrieval.assetInfo(identifier));
      const fallbackName = `EVM Token: ${address}`;

      expect(result).toMatchObject({
        name: fallbackName,
        symbol: fallbackName
      });

      expect(get(assetInfoRetrieval.assetName(identifier))).toEqual(
        fallbackName
      );
      expect(get(assetInfoRetrieval.assetSymbol(identifier))).toEqual(
        fallbackName
      );
    });
  });
});
