<template>
  <v-container>
    <nft-gallery />
  </v-container>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import NftGallery from '@/components/nft/NftGallery.vue';

export default defineComponent({
  name: 'Nft',
  components: { NftGallery }
});
</script>
