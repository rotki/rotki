<script setup lang="ts">
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import { Module, useModuleEnabled } from '@/composables/session/modules';
import NonFungibleBalances from '@/modules/balances/non-fungible/components/NonFungibleBalances.vue';
import { NoteLocation } from '@/modules/common/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.BALANCES_NON_FUNGIBLE,
  },
  name: 'balances-non-fungible',
});

const modules = [Module.NFTS];
const { enabled } = useModuleEnabled(modules[0]);
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
