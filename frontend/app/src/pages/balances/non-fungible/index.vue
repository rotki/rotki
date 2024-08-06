<script setup lang="ts">
import { Module } from '@/types/modules';
import { NoteLocation } from '@/types/notes';

definePage({
  name: 'accounts-balances-non-fungible',
  meta: {
    noteLocation: NoteLocation.ACCOUNTS_BALANCES_NON_FUNGIBLE,
  },
});

const { isModuleEnabled } = useModules();
const modules = [Module.NFTS];
const enabled = isModuleEnabled(modules[0]);
</script>

<template>
  <ModuleNotActive
    v-if="!enabled"
    :modules="modules"
  />
  <NonFungibleBalances
    v-else
    :modules="modules"
  />
</template>
