<template>
  <module-not-active v-if="!anyModuleEnabled" :modules="modules" />
  <deposits v-else />
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import Deposits from '@/components/defi/Deposits.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ModuleMixin from '@/mixins/module-mixin';
import { Module } from '@/types/modules';

@Component({
  components: { ModuleNotActive, Deposits }
})
export default class Protocols extends Mixins(ModuleMixin) {
  readonly modules: Module[] = [
    Module.AAVE,
    Module.COMPOUND,
    Module.MAKERDAO_DSR,
    Module.YEARN,
    Module.YEARN_V2
  ];

  get anyModuleEnabled(): boolean {
    return this.isAnyModuleEnabled(this.modules);
  }
}
</script>
