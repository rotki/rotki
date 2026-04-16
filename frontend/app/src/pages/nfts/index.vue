<script setup lang="ts">
import NftGallery from '@/modules/balances/nft/NftGallery.vue';
import { NoteLocation } from '@/modules/core/common/notes';
import { Module, useModuleEnabled } from '@/modules/session/use-module-enabled';
import ModuleNotActive from '@/modules/settings/modules/ModuleNotActive.vue';

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
