<template>
  <module-not-active v-if="!enabled" :modules="modules" />
  <non-fungible-balances v-else :modules="modules" />
</template>

<script setup lang="ts">
import NonFungibleBalances from '@/components/accounts/balances/NonFungibleBalances.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import { useModules } from '@/composables/session/modules';
import { Module } from '@/types/modules';

const { isModuleEnabled } = useModules();
const modules = [Module.NFTS];
const enabled = isModuleEnabled(modules[0]);
</script>
