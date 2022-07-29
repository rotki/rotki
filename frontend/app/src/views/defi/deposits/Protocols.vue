<template>
  <module-not-active v-if="!anyModuleEnabled" :modules="modules" />
  <deposits v-else />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import Deposits from '@/components/defi/Deposits.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import { useModules } from '@/composables/session';
import { Module } from '@/types/modules';

export default defineComponent({
  components: { ModuleNotActive, Deposits },
  setup() {
    const modules: Module[] = [
      Module.AAVE,
      Module.COMPOUND,
      Module.MAKERDAO_DSR,
      Module.YEARN,
      Module.YEARN_V2
    ];

    const { isAnyModuleEnabled } = useModules();

    return {
      modules,
      anyModuleEnabled: isAnyModuleEnabled(modules)
    };
  }
});
</script>
