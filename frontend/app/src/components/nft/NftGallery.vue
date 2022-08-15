<template>
  <progress-screen v-if="loading && visibleNfts.length === 0">
    {{ $t('nft_gallery.loading') }}
  </progress-screen>
  <no-data-screen v-else-if="noData">
    <template #title>
      {{
        error ? $t('nft_gallery.error_title') : $t('nft_gallery.empty_title')
      }}
    </template>
    <span class="text-subtitle-2 text--secondary">
      {{ error ? error : $t('nft_gallery.empty_subtitle') }}
    </span>
  </no-data-screen>
  <div v-else class="py-4">
    <v-row justify="space-between">
      <v-col>
        <v-row align="center">
          <v-col :cols="isMobile ? '12' : '6'">
            <blockchain-account-selector
              v-model="selectedAccount"
              :label="$t('nft_gallery.select_account')"
              :chains="['ETH']"
              dense
              outlined
              no-padding
              flat
              :usable-addresses="availableAddresses"
            />
          </v-col>
          <v-col :cols="isMobile ? '12' : '6'">
            <v-card flat>
              <div>
                <v-autocomplete
                  v-model="selectedCollection"
                  :label="$t('nft_gallery.select_collection')"
                  single-line
                  clearable
                  hide-details
                  hide-selected
                  :items="collections"
                  outlined
                  background-color=""
                  dense
                />
              </div>
            </v-card>
          </v-col>
          <v-col :cols="isMobile ? '12' : '6'">
            <sorting-selector
              :sort-by="sortBy"
              :sort-properties="sortProperties"
              :sort-desc="sortDesc"
              @update:sort-by="sortBy = $event"
              @update:sort-desc="sortDesc = $event"
            />
          </v-col>
          <v-col :cols="isMobile ? '12' : '6'">
            <pagination v-if="pages > 0" v-model="page" :length="pages" />
          </v-col>
        </v-row>
      </v-col>
      <v-col cols="auto">
        <active-modules :modules="modules" />
      </v-col>
      <v-col cols="auto">
        <refresh-button
          :loading="loading"
          :tooltip="$t('nft_gallery.refresh_tooltip')"
          @refresh="fetchNfts(true)"
        />
      </v-col>
    </v-row>
    <v-row v-if="!premium && visibleNfts.length > 0" justify="center">
      <v-col cols="auto">
        <i18n path="nft_gallery.upgrade">
          <template #limit> {{ limit }}</template>
          <template #link>
            <base-external-link
              :text="$t('upgrade_row.rotki_premium')"
              :href="$interop.premiumURL"
            />
          </template>
        </i18n>
      </v-col>
    </v-row>
    <v-row
      v-if="visibleNfts.length === 0"
      align="center"
      justify="center"
      :class="$style.empty"
    >
      <v-col cols="auto" class="text--secondary text-h6">
        {{ $t('nft_gallery.empty_filter') }}
      </v-col>
    </v-row>
    <v-row v-else>
      <v-col
        v-for="item in visibleNfts"
        :key="item.tokenIdentifier"
        cols="12"
        sm="6"
        md="6"
        lg="3"
        :class="$style.xl"
      >
        <nft-gallery-item :item="item" />
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import { GeneralAccount } from '@rotki/common/lib/account';
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  Ref,
  ref,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import NoDataScreen from '@/components/common/NoDataScreen.vue';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import Pagination from '@/components/helper/Pagination.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import SortingSelector from '@/components/helper/SortingSelector.vue';
import NftGalleryItem from '@/components/nft/NftGalleryItem.vue';
import { useTheme } from '@/composables/common';
import { getPremium } from '@/composables/session';
import i18n from '@/i18n';
import { AssetPriceArray } from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { useSessionStore } from '@/store/session';
import { GalleryNft, Nft, Nfts } from '@/store/session/types';
import { Module } from '@/types/modules';
import { uniqueStrings } from '@/utils/data';

const requestPrices = () => {
  const prices: Ref<AssetPriceArray> = ref([]);
  const priceError = ref('');
  const fetchPrices = async () => {
    try {
      const data = await api.assets.fetchCurrentPrices();
      set(prices, AssetPriceArray.parse(data));
    } catch (e: any) {
      set(priceError, e.message);
    }
  };
  onMounted(fetchPrices);
  return {
    fetchPrices,
    priceError,
    prices
  };
};

function sortNfts(
  sortBy: Ref<'name' | 'priceUsd' | 'collection'>,
  sortDesc: Ref<boolean>,
  a: GalleryNft,
  b: GalleryNft
): number {
  const sortProp = get(sortBy);
  const desc = get(sortDesc);
  const isCollection = sortProp === 'collection';
  const aElement = isCollection ? a.collection.name : a[sortProp];
  const bElement = isCollection ? b.collection.name : b[sortProp];
  if (typeof aElement === 'string' && typeof bElement === 'string') {
    return desc
      ? bElement.localeCompare(aElement, 'en', { sensitivity: 'base' })
      : aElement.localeCompare(bElement, 'en', { sensitivity: 'base' });
  } else if (aElement instanceof BigNumber && bElement instanceof BigNumber) {
    return (
      desc ? bElement.minus(aElement) : aElement.minus(bElement)
    ).toNumber();
  } else if (aElement === null && bElement === null) {
    return 0;
  } else if (aElement && !bElement) {
    return desc ? 1 : -1;
  } else if (!aElement && bElement) {
    return desc ? -1 : 1;
  }
  return 0;
}

const setupNfts = (
  selectedAccount: Ref<GeneralAccount | null>,
  selectedCollection: Ref<string | null>,
  itemsPerPage: Ref<number>,
  page: Ref<number>,
  prices: Ref<AssetPriceArray>
) => {
  const total = ref(0);
  const limit = ref(0);
  const error = ref('');
  const loading = ref(true);
  const perAccount: Ref<Nfts | null> = ref(null);
  const sortBy = ref<'name' | 'priceUsd' | 'collection'>('name');
  const sortDesc = ref(false);
  const sortProperties = [
    {
      text: i18n.t('common.name').toString(),
      value: 'name'
    },
    {
      text: i18n.t('common.price').toString(),
      value: 'priceUsd'
    },
    {
      text: i18n.t('nft_gallery.sort.collection').toString(),
      value: 'collection'
    }
  ];

  const items = computed(() => {
    const account = get(selectedAccount);
    const selection = get(selectedCollection);
    if (account || selection) {
      return get(nfts)
        .filter(({ address, collection }) => {
          const sameAccount = account ? address === account.address : true;
          const sameCollection = selection
            ? selection === collection.name
            : true;
          return sameAccount && sameCollection;
        })
        .sort((a, b) => sortNfts(sortBy, sortDesc, a, b));
    }

    return get(nfts).sort((a, b) => sortNfts(sortBy, sortDesc, a, b));
  });

  const pages = computed(() => {
    return Math.ceil(get(items).length / get(itemsPerPage));
  });

  const visibleNfts = computed(() => {
    const start = (get(page) - 1) * get(itemsPerPage);
    return get(items).slice(start, start + get(itemsPerPage));
  });

  const availableAddresses = computed(() =>
    get(perAccount) ? Object.keys(get(perAccount)!) : []
  );

  const nfts = computed<GalleryNft[]>(() => {
    const addresses: Nfts | null = get(perAccount);
    const value = get(prices);
    if (!addresses) {
      return [];
    }

    const allNfts: GalleryNft[] = [];
    for (const address in addresses) {
      const addressNfts: Nft[] = addresses[address];
      for (const nft of addressNfts) {
        const price = value.find(({ asset }) => asset === nft.tokenIdentifier);
        const { priceEth, priceUsd, ...data } = nft;
        let priceDetails: {
          priceInAsset: BigNumber;
          priceAsset: string;
          priceUsd: BigNumber;
        };
        if (price && price.manuallyInput) {
          priceDetails = {
            priceAsset: price.priceAsset,
            priceInAsset: price.priceInAsset,
            priceUsd: price.usdPrice
          };
        } else {
          priceDetails = {
            priceAsset: 'ETH',
            priceInAsset: priceEth,
            priceUsd
          };
        }

        allNfts.push({ ...data, ...priceDetails, address });
      }
    }
    return allNfts;
  });

  const collections = computed(() => {
    if (!get(nfts)) {
      return [];
    }
    return get(nfts)
      .map(({ collection }) => collection.name ?? '')
      .filter(uniqueStrings);
  });

  const { fetchNfts: nftFetch } = useSessionStore();

  const fetchNfts = async (ignoreCache: boolean = false) => {
    set(loading, true);
    const { message, result } = await nftFetch(ignoreCache);
    if (result) {
      set(total, result.entriesFound);
      set(limit, result.entriesLimit);
      set(perAccount, result.addresses);
    } else {
      set(error, message);
    }
    set(loading, false);
  };

  const noData = computed(
    () =>
      get(visibleNfts).length === 0 &&
      !(get(selectedCollection) || get(selectedAccount))
  );

  onMounted(fetchNfts);

  return {
    total,
    limit,
    visibleNfts,
    fetchNfts,
    pages,
    error,
    availableAddresses,
    collections,
    sortBy,
    sortDesc,
    sortProperties,
    noData,
    loading
  };
};

export default defineComponent({
  name: 'NftGallery',
  components: {
    SortingSelector,
    Pagination,
    ActiveModules,
    BaseExternalLink,
    NoDataScreen,
    RefreshButton,
    ProgressScreen,
    NftGalleryItem
  },
  props: {
    modules: {
      required: true,
      type: Array as PropType<Module[]>
    }
  },
  setup() {
    const { isMobile, breakpoint, width } = useTheme();
    const page = ref(1);

    const itemsPerPage = computed(() => {
      if (get(breakpoint) === 'xs') {
        return 1;
      } else if (get(breakpoint) === 'sm') {
        return 2;
      } else if (get(width) >= 1600) {
        return 10;
      }
      return 8;
    });
    const selectedAccount = ref<GeneralAccount | null>(null);
    const selectedCollection = ref<string | null>(null);
    const premium = getPremium();

    watch(selectedAccount, () => set(page, 1));
    watch(selectedCollection, () => set(page, 1));
    const retrievePrices = requestPrices();

    return {
      selectedAccount,
      selectedCollection,
      page,
      isMobile,
      premium,
      ...retrievePrices,
      ...setupNfts(
        selectedAccount,
        selectedCollection,
        itemsPerPage,
        page,
        retrievePrices.prices
      )
    };
  }
});
</script>

<style module lang="scss">
.empty {
  min-height: 80vh;
}

.xl {
  @media only screen and (min-width: 1600px) {
    flex: 0 0 20% !important;
    max-width: 20% !important;
  }
}
</style>
