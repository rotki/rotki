<template>
  <module-not-active v-if="!anyModuleEnabled" :modules="modules" />
  <lending v-else />
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import Lending from '@/components/defi/Lending.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import DefiModuleMixin from '@/mixins/defi-module-mixin';
import {
  MODULE_AAVE,
  MODULE_COMPOUND,
  MODULE_MAKERDAO_DSR,
  MODULE_YEARN
} from '@/services/session/consts';
import { SupportedModules } from '@/services/session/types';

@Component({
  components: { ModuleNotActive, Lending }
})
export default class Protocols extends Mixins(DefiModuleMixin) {
  readonly modules: SupportedModules[] = [
    MODULE_AAVE,
    MODULE_COMPOUND,
    MODULE_MAKERDAO_DSR,
    MODULE_YEARN
  ];

  get anyModuleEnabled(): boolean {
    return this.isAnyModuleEnabled(this.modules);
  }
}
</script>
