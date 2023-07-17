<script setup lang="ts">
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

<template>
  <ModuleNotActive v-if="!anyModuleEnabled" :modules="modules" />
  <Borrowing v-else :modules="modules" />
</template>
