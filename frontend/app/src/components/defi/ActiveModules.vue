<template>
  <v-row justify="end">
    <v-col cols="auto">
      <v-sheet outlined :style="style">
        <v-row align="center" justify="center" class="pa-2">
          <v-col v-for="module in enabled" :key="module" cols="auto">
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <v-img
                  width="24px"
                  contain
                  :src="icon(module)"
                  v-bind="attrs"
                  v-on="on"
                />
              </template>
              <div>
                <div> The following addresses are queried</div>
                <div v-for="address in addresses(module)" :key="address">
                  {{ address }}
                </div>
              </div>
            </v-tooltip>
          </v-col>
          <v-col v-for="module in disabled" :key="module" cols="auto">
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <v-img
                  width="24px"
                  contain
                  class="active-modules__disabled"
                  :src="icon(module)"
                  v-bind="attrs"
                  v-on="on"
                />
              </template>
              <div>
                <div>This module is not enabled.</div>
                <div>Visit the Defi settings to enable it.</div>
              </div>
            </v-tooltip>
          </v-col>
        </v-row>
      </v-sheet>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import { DEFI_MODULES } from '@/components/defi/wizard/consts';
import { QueriedAddresses, SupportedModules } from '@/services/session/types';

@Component({
  name: 'ActiveModules',
  computed: {
    ...mapGetters('session', ['activeModules']),
    ...mapState('session', ['queriedAddresses'])
  }
})
export default class ActiveModules extends Vue {
  @Prop({ required: true, type: Array })
  modules!: SupportedModules[];

  activeModules!: SupportedModules[];
  queriedAddresses!: QueriedAddresses;

  get style() {
    return {
      width: `${this.modules.length * 48}px`
    };
  }

  get enabled(): SupportedModules[] {
    return this.modules.filter(module => this.activeModules.includes(module));
  }

  get disabled(): SupportedModules[] {
    return this.modules.filter(module => !this.activeModules.includes(module));
  }

  addresses(module: SupportedModules): string[] {
    return this.queriedAddresses[module] ?? [];
  }

  name(module: string): string {
    const data = DEFI_MODULES.find(value => value.identifier === module);
    return data?.name ?? '';
  }

  icon(module: SupportedModules): string {
    const data = DEFI_MODULES.find(value => value.identifier === module);
    return data?.icon ?? '';
  }
}
</script>

<style scoped lang="scss">
.active-modules {
  &__disabled {
    filter: grayscale(100%);
  }
}
</style>
