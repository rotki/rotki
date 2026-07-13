<script setup lang="ts">
import { msg } from '@/message-key';
import NonFungibleBalances from '@/modules/balances/non-fungible/components/NonFungibleBalances.vue';
import { NoteLocation } from '@/modules/core/common/notes';
import { Module, useModuleEnabled } from '@/modules/session/use-module-enabled';
import ModuleNotActive from '@/modules/settings/modules/ModuleNotActive.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.balances_sub.non_fungible_balances'), icon: 'lu-image', parent: '/balances/', order: 40, drawer: 'balances-non-fungible' },
    noteLocation: NoteLocation.BALANCES_NON_FUNGIBLE,
  },
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
