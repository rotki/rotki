<template>
  <module-not-active v-if="!anyModuleEnabled" :modules="modules" />
  <lending v-else />
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import Lending from '@/components/defi/Lending.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ModuleMixin from '@/mixins/module-mixin';
import { Module } from '@/services/session/consts';

@Component({
  components: { ModuleNotActive, Lending }
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
