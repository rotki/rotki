<script setup lang="ts">
import { Module } from '@/types/modules';

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
