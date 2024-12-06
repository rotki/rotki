<script setup lang="ts">
import { Module } from '@/types/modules';
import { useModules } from '@/composables/session/modules';
import Deposits from '@/components/defi/Deposits.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';

definePage({
  name: 'defi-deposits-protocols',
});

const modules: Module[] = [Module.AAVE, Module.COMPOUND, Module.MAKERDAO_DSR, Module.YEARN, Module.YEARN_V2];

const { isAnyModuleEnabled } = useModules();
const enabled = isAnyModuleEnabled(modules);
</script>

<template>
  <ModuleNotActive
    v-if="!enabled"
    :modules="modules"
  />
  <Deposits v-else />
</template>
