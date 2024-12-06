<script setup lang="ts">
import { Module } from '@/types/modules';
import { NoteLocation } from '@/types/notes';
import { useModules } from '@/composables/session/modules';
import NftGallery from '@/components/nft/NftGallery.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';

definePage({
  meta: {
    noteLocation: NoteLocation.NFTS,
  },
  name: 'nfts',
});

const modules = [Module.NFTS];
const { isModuleEnabled } = useModules();
const enabled = isModuleEnabled(modules[0]);
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
