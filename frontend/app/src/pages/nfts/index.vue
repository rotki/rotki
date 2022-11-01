<template>
  <v-container>
    <module-not-active v-if="!enabled" :modules="modules" />
    <nft-gallery v-else :modules="modules" />
  </v-container>
</template>

<script setup lang="ts">
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import NftGallery from '@/components/nft/NftGallery.vue';
import { useModules } from '@/composables/session/modules';
import { Module } from '@/types/modules';

const modules = [Module.NFTS];
const { isModuleEnabled } = useModules();
const enabled = isModuleEnabled(modules[0]);
</script>
