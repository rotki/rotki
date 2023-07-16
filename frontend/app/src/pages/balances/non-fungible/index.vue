<script setup lang="ts">
import { Module } from '@/types/modules';

const { isModuleEnabled } = useModules();
const modules = [Module.NFTS];
const enabled = isModuleEnabled(modules[0]);
</script>

<template>
  <ModuleNotActive v-if="!enabled" :modules="modules" />
  <NonFungibleBalances v-else :modules="modules" />
</template>
