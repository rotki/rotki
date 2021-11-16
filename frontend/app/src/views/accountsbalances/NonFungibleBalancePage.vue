<template>
  <module-not-active v-if="!isModuleEnabled" :modules="modules" />
  <non-fungible-balances v-else :modules="modules" />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import NonFungibleBalances from '@/components/accounts/balances/NonFungibleBalances.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import { setupModuleEnabled } from '@/composables/session';
import { Module } from '@/types/modules';

export default defineComponent({
  name: 'NonFungibleBalancePage',
  components: { ModuleNotActive, NonFungibleBalances },
  setup() {
    const { isModuleEnabled } = setupModuleEnabled();
    const modules = [Module.NFTS];
    return {
      modules: modules,
      isModuleEnabled: isModuleEnabled(modules[0])
    };
  }
});
</script>
