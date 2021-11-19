<template>
  <v-row v-if="visibleModules.length > 0">
    <v-col>
      <div class="font-weight-medium">{{ $t('module_activator.title') }}</div>
      <div class="text-caption text--secondary">
        {{ $t('module_activator.subtitle') }}
      </div>
      <v-btn-toggle
        v-model="enabledModules"
        multiple
        class="mt-2"
        @change="updateSelection($event)"
      >
        <v-btn
          v-for="module in visibleModules"
          :key="module.identifier"
          icon
          :value="module.identifier"
          color="primary"
          depressed
          cols="auto"
        >
          <v-tooltip top open-delay="400">
            <template #activator="{ on, attrs }">
              <v-img
                height="24px"
                width="24px"
                contain
                :src="module.icon"
                v-bind="attrs"
                v-on="on"
              />
            </template>
            <span>{{ module.name }}</span>
          </v-tooltip>
        </v-btn>
      </v-btn-toggle>
      <div class="text-caption text--secondary mt-1 mb-2">
        {{ $t('module_activator.hint') }}
      </div>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Emit, Mixins } from 'vue-property-decorator';
import { SUPPORTED_MODULES } from '@/components/defi/wizard/consts';
import { SupportedModule } from '@/components/defi/wizard/types';
import ModuleMixin from '@/mixins/module-mixin';
import { Module } from '@/types/modules';

@Component({
  name: 'ModuleActivator'
})
export default class ModuleActivator extends Mixins(ModuleMixin) {
  readonly modules = SUPPORTED_MODULES;
  enabledModules: Module[] = [];

  @Emit('update:selection')
  updateSelection(_modules: string[]) {}

  hasAddresses(module: Module): boolean {
    const queriedAddresses = this.queriedAddresses[module];
    if (queriedAddresses) {
      return queriedAddresses.length > 0;
    }
    return false;
  }

  get visibleModules(): SupportedModule[] {
    return SUPPORTED_MODULES.filter(module => {
      const identifier = module.identifier;
      const isActive = this.activeModules.includes(identifier);
      const activeWithQueried = isActive && this.hasAddresses(identifier);
      return activeWithQueried || !isActive;
    });
  }

  async mounted() {
    await this.fetchQueriedAddresses();
  }
}
</script>
