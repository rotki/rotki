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
  <div v-else>
    <v-row justify="space-between" align="center">
      <v-col>
        <v-row align="center">
          <v-col :cols="isMobile ? '12' : 'auto'">
            <blockchain-account-selector
              v-model="selectedAccount"
              :label="$t('nft_gallery.select_account')"
              :chains="['ETH']"
              dense
              outlined
              no-padding
              flat
              :usable-addresses="availableAddresses"
              :max-width="isMobile ? '100%' : '250px'"
            />
          </v-col>
          <v-col :cols="isMobile ? '12' : 'auto'">
            <v-card flat :max-width="isMobile ? '100%' : '250px'">
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
          <v-col :cols="isMobile ? '12' : 'auto'">
            <sorting-selector
              :sort-by="sortBy"
              :sort-properties="sortProperties"
              :sort-desc="sortDesc"
              @update:sort-by="sortBy = $event"
              @update:sort-desc="sortDesc = $event"
            />
          </v-col>
          <v-col :cols="isMobile ? '12' : 'auto'">
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
          @refresh="fetchNfts({ ignoreCache: true })"
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
import { ActionResult } from '@rotki/common/lib/data';
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  Ref,
  ref,
  watch
} from '@vue/composition-api';
import { Dispatch } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import NoDataScreen from '@/components/common/NoDataScreen.vue';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import Pagination from '@/components/helper/Pagination.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import SortingSelector from '@/components/helper/SortingSelector.vue';
import NftGalleryItem from '@/components/nft/NftGalleryItem.vue';
import { setupThemeCheck } from '@/composables/common';
import i18n from '@/i18n';
import { AssetPriceArray } from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { SessionActions } from '@/store/session/const';
import { GalleryNft, Nft, NftResponse, Nfts } from '@/store/session/types';
import { useStore } from '@/store/utils';
import { Module } from '@/types/modules';
import { uniqueStrings } from '@/utils/data';

const requestPrices = () => {
  const prices: Ref<AssetPriceArray> = ref([]);
  const priceError = ref('');
  const fetchPrices = async () => {
    try {
      const data = await api.assets.fetchCurrentPrices();
      prices.value = AssetPriceArray.parse(data);
    } catch (e: any) {
      priceError.value = e.message;
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
  const sortProp = sortBy.value;
  const desc = sortDesc.value;
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
  dispatch: Dispatch,
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
      text: i18n.t('nft_gallery.sort.name').toString(),
      value: 'name'
    },
    {
      text: i18n.t('nft_gallery.sort.price').toString(),
      value: 'priceUsd'
    },
    {
      text: i18n.t('nft_gallery.sort.collection').toString(),
      value: 'collection'
    }
  ];

  const items = computed(() => {
    const account = selectedAccount.value;
    const selection = selectedCollection.value;
    if (account || selection) {
      return nfts.value
        .filter(({ address, collection }) => {
          const sameAccount = account ? address === account.address : true;
          const sameCollection = selection
            ? selection === collection.name
            : true;
          return sameAccount && sameCollection;
        })
        .sort((a, b) => sortNfts(sortBy, sortDesc, a, b));
    }

    return nfts.value.sort((a, b) => sortNfts(sortBy, sortDesc, a, b));
  });

  const pages = computed(() => {
    return Math.ceil(items.value.length / itemsPerPage.value);
  });

  const visibleNfts = computed(() => {
    const start = (page.value - 1) * itemsPerPage.value;
    return items.value.slice(start, start + itemsPerPage.value);
  });

  const availableAddresses = computed(() =>
    perAccount.value ? Object.keys(perAccount.value) : []
  );

  const nfts = computed<GalleryNft[]>(() => {
    const addresses: Nfts | null = perAccount.value;
    const value = prices.value;
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
    if (!nfts.value) {
      return [];
    }
    return nfts.value
      .map(({ collection }) => collection.name ?? '')
      .filter(uniqueStrings);
  });

  const fetchNfts = async (payload?: { ignoreCache: boolean }) => {
    loading.value = true;
    const { message, result }: ActionResult<NftResponse> = await dispatch(
      `session/${SessionActions.FETCH_NFTS}`,
      payload
    );
    if (result) {
      total.value = result.entriesFound;
      limit.value = result.entriesLimit;
      perAccount.value = result.addresses;
    } else {
      error.value = message;
    }
    loading.value = false;
  };

  const noData = computed(
    () =>
      visibleNfts.value.length === 0 &&
      !(selectedCollection.value || selectedAccount.value)
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
    const { isMobile, breakpoint, width } = setupThemeCheck();
    const { dispatch, state } = useStore();

    const page = ref(1);

    const itemsPerPage = computed(() => {
      if (breakpoint.value === 'xs') {
        return 1;
      } else if (breakpoint.value === 'sm') {
        return 2;
      } else if (width.value >= 1600) {
        return 10;
      }
      return 8;
    });
    const selectedAccount = ref<GeneralAccount | null>(null);
    const selectedCollection = ref<string | null>(null);
    const premium = computed(() => state.session?.premium);

    watch(selectedAccount, () => (page.value = 1));
    watch(selectedCollection, () => (page.value = 1));
    const retrievePrices = requestPrices();

    return {
      selectedAccount,
      selectedCollection,
      page,
      isMobile,
      premium,
      ...retrievePrices,
      ...setupNfts(
        dispatch,
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
