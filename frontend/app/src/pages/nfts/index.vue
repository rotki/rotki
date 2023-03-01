<script setup lang="ts">
import { Module } from '@/types/modules';

const modules = [Module.NFTS];
const { isModuleEnabled } = useModules();
const enabled = isModuleEnabled(modules[0]);
</script>

<template>
  <v-container>
    <module-not-active v-if="!enabled" :modules="modules" />
    <nft-gallery v-else :modules="modules" />
  </v-container>
</template>
