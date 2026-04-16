<script setup lang="ts">
import NonFungibleBalances from '@/modules/balances/non-fungible/components/NonFungibleBalances.vue';
import { NoteLocation } from '@/modules/core/common/notes';
import { Module, useModuleEnabled } from '@/modules/session/use-module-enabled';
import ModuleNotActive from '@/modules/settings/modules/ModuleNotActive.vue';

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
