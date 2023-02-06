<script setup lang="ts">
import Deposits from '@/components/defi/Deposits.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import { Module } from '@/types/modules';

const modules: Module[] = [
  Module.AAVE,
  Module.COMPOUND,
  Module.MAKERDAO_DSR,
  Module.YEARN,
  Module.YEARN_V2
];

const { isAnyModuleEnabled } = useModules();
const enabled = isAnyModuleEnabled(modules);
</script>

<template>
  <module-not-active v-if="!enabled" :modules="modules" />
  <deposits v-else />
</template>
