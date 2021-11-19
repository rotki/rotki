<template>
  <module-not-active v-if="!anyModuleEnabled" :modules="modules" />
  <liabilities v-else :modules="modules" />
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import Liabilities from '@/components/defi/Liabilities.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ModuleMixin from '@/mixins/module-mixin';
import { Module } from '@/types/modules';

@Component({
  components: { ModuleNotActive, Liabilities }
})
export default class DecentralizedBorrowing extends Mixins(ModuleMixin) {
  readonly modules: Module[] = [
    Module.AAVE,
    Module.COMPOUND,
    Module.MAKERDAO_VAULTS,
    Module.LIQUITY
  ];

  get anyModuleEnabled(): boolean {
    return this.isAnyModuleEnabled(this.modules);
  }
}
</script>
