<template>
  <module-not-active v-if="!anyModuleEnabled" :modules="modules" />
  <liabilities v-else :modules="modules" />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import Liabilities from '@/components/defi/Liabilities.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import { useModules } from '@/composables/session';
import { Module } from '@/types/modules';

export default defineComponent({
  components: { ModuleNotActive, Liabilities },
  setup() {
    const modules: Module[] = [
      Module.AAVE,
      Module.COMPOUND,
      Module.MAKERDAO_VAULTS,
      Module.LIQUITY
    ];

    const { isAnyModuleEnabled } = useModules();

    return {
      modules,
      anyModuleEnabled: isAnyModuleEnabled(modules)
    };
  }
});
</script>
