<script setup lang="ts">
import type { GalleryNft } from '@/types/nfts';
import NftGalleryItem from '@/components/nft/NftGalleryItem.vue';

interface Props {
  items: GalleryNft[];
}

defineProps<Props>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div
    v-if="items.length === 0"
    class="min-h-[60vh] flex justify-center items-center text-rui-text-secondary text-h6"
    role="status"
    :aria-label="t('nft_gallery.empty_filter')"
  >
    {{ t('nft_gallery.empty_filter') }}
  </div>
  <div
    v-else
    class="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5 gap-4"
    role="grid"
    aria-label="NFT Gallery Grid"
  >
    <div
      v-for="item in items"
      :key="item.tokenIdentifier"
      v-memo="[item.tokenIdentifier, item.name, item.price]"
      class="overflow-hidden"
      role="gridcell"
    >
      <NftGalleryItem :item="item" />
    </div>
  </div>
</template>
