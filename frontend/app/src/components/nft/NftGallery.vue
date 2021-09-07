<template>
  <progress-screen v-if="loading && visibleNfts.length === 0">
    {{ $t('nft_gallery.loading') }}
  </progress-screen>
  <no-data-screen v-else-if="visibleNfts.length === 0">
    <template #title>{{ $t('nft_gallery.empty_title') }}</template>
    <span class="text-subtitle-2 text--secondary">
      {{ $t('nft_gallery.empty_subtitle') }}
    </span>
  </no-data-screen>
  <div v-else>
    <v-row justify="space-between">
      <v-col>
        <blockchain-account-selector
          v-model="selectedAccount"
          :chains="['ETH']"
          dense
          outlined
          no-padding
          flat
          :usable-addresses="availableAddresses"
          max-width="350px"
        />
      </v-col>
      <v-col cols="auto">
        <refresh-button
          :loading="loading"
          :tooltip="$t('nft_gallery.refresh_tooltip')"
          @refresh="fetchNfts"
        />
      </v-col>
    </v-row>
    <v-row>
      <v-col
        v-for="item in visibleNfts"
        :key="item.tokenIdentifier"
        cols="12"
        sm="6"
        md="6"
        lg="4"
        xl="3"
      >
        <nft-gallery-item :item="item" />
      </v-col>
    </v-row>
    <v-pagination
      v-model="page"
      :length="pages"
      :class="isMobile ? 'mt-2' : 'mt-5'"
    />
  </div>
</template>

<script lang="ts">
import { ActionResult } from '@rotki/common/lib/data';
import {
  computed,
  defineComponent,
  onMounted,
  ref
} from '@vue/composition-api';
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

export default defineComponent({
  name: 'NftGallery',
  components: { NoDataScreen, RefreshButton, ProgressScreen, NftGalleryItem },
  setup() {
    const { isMobile } = setupThemeCheck();
    const { dispatch } = useStore();
    const total = ref(0);
    const limit = ref(0);
    const error = ref('');
    const loading = ref(true);
    const page = ref(1);
    const nfts = ref<NftWithAddress[]>([]);
    const availableAddresses = ref<string[]>([]);
    const itemsPerPage = computed(() => (isMobile.value ? 1 : 8));
    const selectedAccount = ref<GeneralAccount | null>(null);

    const items = computed(() => {
      const value = selectedAccount.value;
      if (value) {
        return nfts.value.filter(({ address }) => address === value.address);
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
        const { addresses } = result;
        availableAddresses.value = Object.keys(addresses);
        for (const address in addresses) {
          const addressNfts = addresses[address];
          for (const nft of addressNfts) {
            allNfts.push({ ...nft, address });
          }
        }
        nfts.value = allNfts;
      } else {
        error.value = message;
      }
      loading.value = false;
    };

    onMounted(fetchNfts);

    return {
      total,
      limit,
      visibleNfts,
      fetchNfts,
      availableAddresses,
      selectedAccount,
      loading,
      page,
      pages,
      isMobile
    };
  }
});
</script>
