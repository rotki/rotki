<script setup lang="ts">
import { Module } from '@/types/modules';

const { isModuleEnabled } = useModules();
const modules = [Module.NFTS];
const enabled = isModuleEnabled(modules[0]);
</script>

<template>
  <module-not-active v-if="!enabled" :modules="modules" />
  <non-fungible-balances v-else :modules="modules" />
</template>
