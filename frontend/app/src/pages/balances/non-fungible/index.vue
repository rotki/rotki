<script setup lang="ts">
import { Module } from '@/types/modules';
import { NoteLocation } from '@/types/notes';
import { useModules } from '@/composables/session/modules';
import NonFungibleBalances from '@/components/accounts/balances/NonFungibleBalances.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';

definePage({
  meta: {
    noteLocation: NoteLocation.BALANCES_NON_FUNGIBLE,
  },
  name: 'balances-non-fungible',
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
