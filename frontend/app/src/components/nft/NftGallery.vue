<template>
  <div>
    <v-row>
      <v-col
        v-for="item in nfts"
        :key="item.tokenIdentifier"
        cols="12"
        sm="6"
        md="6"
        lg="3"
      >
        <nft-gallery-item :item="item" />
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import { ActionResult } from '@rotki/common/lib/data';
import { defineComponent, onMounted, ref } from '@vue/composition-api';
import NftGalleryItem from '@/components/nft/NftGalleryItem.vue';
import { NftWithAddress } from '@/components/nft/types';
import { SessionActions } from '@/store/session/const';
import { NftResponse } from '@/store/session/types';
import { useStore } from '@/store/utils';

export default defineComponent({
  name: 'NftGallery',
  components: { NftGalleryItem },
  setup() {
    const { dispatch } = useStore();
    const total = ref(0);
    const limit = ref(0);
    const error = ref('');
    const nfts = ref<NftWithAddress[]>([]);

    const fetchNfts = async () => {
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
    };

    onMounted(fetchNfts);

    return {
      total,
      limit,
      nfts
    };
  }
});
</script>

<style scoped></style>
