import type { ComputedRef, DeepReadonly, Ref } from 'vue';
import type { GalleryNft, Nft, Nfts } from '@/modules/assets/nfts';
import type { NftPrice } from '@/modules/assets/prices/price-types';
import { keyBy } from 'es-toolkit';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useNfts } from '@/modules/assets/use-asset-nft';

interface UseNftGalleryDataReturn {
  error: Readonly<Ref<string>>;
  fetchNfts: (ignoreCache?: boolean) => Promise<void>;
  fetchPrices: () => Promise<void>;
  limit: Readonly<Ref<number>>;
  loading: Readonly<Ref<boolean>>;
  nftLimited: ComputedRef<boolean>;
  nfts: ComputedRef<GalleryNft[]>;
  perAccount: Ref<Nfts | null>;
  priceError: Readonly<Ref<string>>;
  prices: DeepReadonly<Ref<Record<string, NftPrice>>>;
  total: Readonly<Ref<number>>;
}

export function useNftGalleryData(): UseNftGalleryDataReturn {
  // State
  const prices = ref<Record<string, NftPrice>>({});
  const priceError = shallowRef<string>('');
  const total = shallowRef<number>(0);
  const limit = shallowRef<number>(0);
  const error = shallowRef<string>('');
  const loading = shallowRef<boolean>(true);
  const perAccount = shallowRef<Nfts | null>(null);

  // API composables
  const { fetchNfts: nftFetch } = useNfts();
  const { fetchNftsPrices } = useAssetPricesApi();

  // Computed properties
  const nfts = computed<GalleryNft[]>(() => {
    const addresses: Nfts | null = get(perAccount);
    const value = get(prices);
    if (!addresses)
      return [];

    const allNfts: GalleryNft[] = [];
    for (const address in addresses) {
      const addressNfts: Nft[] = addresses[address];
      for (const nft of addressNfts) {
        const price = value[nft.tokenIdentifier];

        if (price?.manuallyInput) {
          const { priceAsset, priceInAsset, price: priceVal } = price;
          allNfts.push({ ...nft, address, priceAsset, priceInAsset, price: priceVal });
        }
        else {
          allNfts.push({ ...nft, address });
        }
      }
    }
    return allNfts;
  });

  const nftLimited = computed<boolean>(() => get(error).includes('limit'));

  // Methods
  async function fetchNfts(ignoreCache = false): Promise<void> {
    set(loading, true);
    const { message, result } = await nftFetch(ignoreCache);
    if (result) {
      set(total, result.entriesFound);
      set(limit, result.entriesLimit);
      set(perAccount, result.addresses);
    }
    else {
      set(error, message);
    }
    set(loading, false);
  }

  async function fetchPrices(): Promise<void> {
    try {
      const data = await fetchNftsPrices();
      set(prices, keyBy(data, item => item.asset));
    }
    catch (error_: any) {
      set(priceError, error_.message);
    }
  }

  return {
    error: readonly(error),
    fetchNfts,
    fetchPrices,
    limit: readonly(limit),
    loading: readonly(loading),
    nftLimited,
    nfts,
    perAccount,
    priceError: readonly(priceError),
    prices: readonly(prices),
    total: readonly(total),
  };
}
