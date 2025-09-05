import type { ComputedRef, Ref } from 'vue';
import type { GalleryNft, Nft, Nfts } from '@/types/nfts';
import type { NftPrice } from '@/types/prices';
import { keyBy } from 'es-toolkit';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { useNfts } from '@/composables/assets/nft';

interface UseNftGalleryDataReturn {
  error: Ref<string>;
  fetchNfts: (ignoreCache?: boolean) => Promise<void>;
  fetchPrices: () => Promise<void>;
  limit: Ref<number>;
  loading: Ref<boolean>;
  nftLimited: ComputedRef<boolean>;
  nfts: ComputedRef<GalleryNft[]>;
  perAccount: Ref<Nfts | null>;
  priceError: Ref<string>;
  prices: Ref<Record<string, NftPrice>>;
  total: Ref<number>;
}

export function useNftGalleryData(): UseNftGalleryDataReturn {
  // State
  const prices = ref<Record<string, NftPrice>>({});
  const priceError = ref<string>('');
  const total = ref<number>(0);
  const limit = ref<number>(0);
  const error = ref<string>('');
  const loading = ref<boolean>(true);
  const perAccount = ref<Nfts | null>(null);

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
          const { priceAsset, priceInAsset, usdPrice: priceUsd } = price;
          allNfts.push({ ...nft, address, priceAsset, priceInAsset, priceUsd });
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
    error,
    fetchNfts,
    fetchPrices,
    limit,
    loading,
    nftLimited,
    nfts,
    perAccount,
    priceError,
    prices,
    total,
  };
}
