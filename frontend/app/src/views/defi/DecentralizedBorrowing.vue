<template>
  <module-not-active v-if="!anyModuleEnabled" :modules="modules" />
  <borrowing v-else :modules="modules" />
</template>

<script setup lang="ts">
import Borrowing from '@/components/defi/Borrowing.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import { useModules } from '@/composables/session/modules';
import { Module } from '@/types/modules';

const modules: Module[] = [
  Module.AAVE,
  Module.COMPOUND,
  Module.MAKERDAO_VAULTS,
  Module.LIQUITY
];

const { isAnyModuleEnabled } = useModules();
const anyModuleEnabled = isAnyModuleEnabled(modules);
</script>
