<template>
  <progress-screen v-if="loading && visibleNfts.length === 0">
    {{ $t('nft_gallery.loading') }}
  </progress-screen>
  <div v-else class="mt-2">
    <v-row justify="end">
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
    <v-pagination v-model="page" :length="pages" class="mt-5" />
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
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import NftGalleryItem from '@/components/nft/NftGalleryItem.vue';
import { NftWithAddress } from '@/components/nft/types';
import { setupThemeCheck } from '@/composables/theme';
import { SessionActions } from '@/store/session/const';
import { NftResponse } from '@/store/session/types';
import { useStore } from '@/store/utils';

export default defineComponent({
  name: 'NftGallery',
  components: { RefreshButton, ProgressScreen, NftGalleryItem },
  setup() {
    const { isMobile } = setupThemeCheck();
    const { dispatch } = useStore();
    const total = ref(0);
    const limit = ref(0);
    const error = ref('');
    const loading = ref(true);
    const page = ref(1);
    const nfts = ref<NftWithAddress[]>([]);
    const itemsPerPage = computed(() => (isMobile.value ? 1 : 8));

    const pages = computed(() => {
      return Math.ceil(nfts.value.length / itemsPerPage.value);
    });

    const visibleNfts = computed(() => {
      const start = (page.value - 1) * itemsPerPage.value;
      return nfts.value.slice(start, start + itemsPerPage.value);
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
      loading,
      page,
      pages
    };
  }
});
</script>

<style scoped></style>
