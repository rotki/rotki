<template>
  <progress-screen v-if="loading && visibleNfts.length === 0">
    {{ $t('nft_gallery.loading') }}
  </progress-screen>
  <no-data-screen v-else-if="noData">
    <template #title>{{ $t('nft_gallery.empty_title') }}</template>
    <span class="text-subtitle-2 text--secondary">
      {{ $t('nft_gallery.empty_subtitle') }}
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
            <v-pagination v-if="pages > 0" v-model="page" :length="pages" />
          </v-col>
        </v-row>
      </v-col>
      <v-col cols="auto">
        <refresh-button
          :loading="loading"
          :tooltip="$t('nft_gallery.refresh_tooltip')"
          @refresh="fetchNfts"
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
import { ActionResult } from '@rotki/common/lib/data';
import {
  computed,
  defineComponent,
  onMounted,
  Ref,
  ref,
  watch
} from '@vue/composition-api';
import { Dispatch } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import NoDataScreen from '@/components/common/NoDataScreen.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import NftGalleryItem from '@/components/nft/NftGalleryItem.vue';
import { NftWithAddress } from '@/components/nft/types';
import { setupThemeCheck } from '@/composables/common';
import { SessionActions } from '@/store/session/const';
import { NftResponse } from '@/store/session/types';
import { useStore } from '@/store/utils';
import { GeneralAccount } from '@/typing/types';

const setupNfts = (
  dispatch: Dispatch,
  selectedAccount: Ref<GeneralAccount | null>,
  selectedCollection: Ref<string | null>,
  itemsPerPage: Ref<number>,
  page: Ref<number>
) => {
  const total = ref(0);
  const limit = ref(0);
  const error = ref('');
  const loading = ref(true);
  const availableAddresses = ref<string[]>([]);
  const nfts = ref<NftWithAddress[]>([]);
  const collections = ref<string[]>([]);

  const items = computed(() => {
    const account = selectedAccount.value;
    const selection = selectedCollection.value;
    if (account || selection) {
      return nfts.value.filter(({ address, collection }) => {
        const sameAccount = account ? address === account.address : true;
        const sameCollection = selection ? selection === collection.name : true;
        return sameAccount && sameCollection;
      });
    }
    return nfts.value;
  });

  const pages = computed(() => {
    return Math.ceil(items.value.length / itemsPerPage.value);
  });

  const visibleNfts = computed(() => {
    const start = (page.value - 1) * itemsPerPage.value;
    return items.value.slice(start, start + itemsPerPage.value);
  });

  const fetchNfts = async () => {
    loading.value = true;
    const { message, result }: ActionResult<NftResponse> = await dispatch(
      `session/${SessionActions.FETCH_NFTS}`
    );
    if (result) {
      total.value = result.entriesFound;
      limit.value = result.entriesLimit;

      const allNfts: NftWithAddress[] = [];
      const allCollections: string[] = [];
      const { addresses } = result;
      availableAddresses.value = Object.keys(addresses);
      for (const address in addresses) {
        const addressNfts = addresses[address];
        for (const nft of addressNfts) {
          if (!allCollections.includes(nft.collection.name)) {
            allCollections.push(nft.collection.name);
          }
          allNfts.push({ ...nft, address });
        }
      }
      nfts.value = allNfts;
      collections.value = allCollections;
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
    availableAddresses,
    collections,
    noData,
    loading
  };
};

export default defineComponent({
  name: 'NftGallery',
  components: {
    BaseExternalLink,
    NoDataScreen,
    RefreshButton,
    ProgressScreen,
    NftGalleryItem
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

    return {
      selectedAccount,
      selectedCollection,
      page,
      isMobile,
      premium,
      ...setupNfts(
        dispatch,
        selectedAccount,
        selectedCollection,
        itemsPerPage,
        page
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
