<template>
  <v-card class="mx-auto">
    <v-img
      :src="item.imageUrl"
      contain
      aspect-ratio="1"
      :style="{
        'background-color': `#${item.backgroundColor}`
      }"
    />
    <v-card-title>
      <span class="text-truncate">{{ item.name }}</span>
      <v-spacer />
      <amount-display
        class="text--secondary"
        :value="item.priceEth"
        asset="ETH"
      />
    </v-card-title>
    <v-card-actions>
      <v-spacer />
      <icon-link :url="item.permalink" />
    </v-card-actions>
  </v-card>
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import IconLink from '@/components/base/IconLink.vue';
import { NftWithAddress } from '@/components/nft/types';

export default defineComponent({
  name: 'NftGalleryItem',
  components: { IconLink },
  props: {
    item: {
      required: true,
      type: Object as PropType<NftWithAddress>
    }
  }
});
</script>

<style scoped></style>
