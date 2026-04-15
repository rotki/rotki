<script setup lang="ts">
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import NftGallery from '@/components/nft/NftGallery.vue';
import { Module, useModuleEnabled } from '@/composables/session/modules';
import { NoteLocation } from '@/modules/common/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.NFTS,
  },
  name: 'nfts',
});

const modules = [Module.NFTS];
const { enabled } = useModuleEnabled(modules[0]);
</script>

<template>
  <div
    v-if="!enabled"
    class="container"
  >
    <ModuleNotActive :modules="modules" />
  </div>
  <NftGallery
    v-else
    :modules="modules"
  />
</template>
