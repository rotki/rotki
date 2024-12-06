<script setup lang="ts">
import { Module } from '@/types/modules';
import { useModules } from '@/composables/session/modules';
import Borrowing from '@/components/defi/Borrowing.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';

definePage({
  name: 'defi-liabilities',
});

const modules: Module[] = [Module.AAVE, Module.COMPOUND, Module.MAKERDAO_VAULTS, Module.LIQUITY];

const { isAnyModuleEnabled } = useModules();
const anyModuleEnabled = isAnyModuleEnabled(modules);
</script>

<template>
  <ModuleNotActive
    v-if="!anyModuleEnabled"
    :modules="modules"
  />
  <Borrowing
    v-else
    :modules="modules"
  />
</template>
