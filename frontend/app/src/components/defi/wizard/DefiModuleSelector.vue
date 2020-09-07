<template>
  <v-autocomplete
    :value="selectedModules"
    :search-input.sync="search"
    :items="supportedModules"
    hide-details
    hide-selected
    hide-no-data
    clearables
    multiple
    chips
    :disabled="loading"
    :loading="loading"
    :open-on-clear="false"
    label="Select modules(s)"
    item-text="name"
    item-value="identifier"
    class="defi-module-selector"
    @input="update"
  >
    <template #selection="data">
      <v-chip
        :id="`defi-module-${data.item.identifier}`"
        close
        pill
        @click:close="unselect(data.item.identifier)"
      >
        <v-avatar left>
          <v-img width="26px" contain max-height="24px" :src="data.item.icon" />
        </v-avatar>
        <span> {{ data.item.name }}</span>
      </v-chip>
    </template>
    <template #item="data">
      <span v-bind="data.attrs" class="d-flex flex-row align-center">
        <v-img
          width="26px"
          contain
          position="left"
          max-height="24px"
          :src="data.item.icon"
        />
        <span class="ml-2"> {{ data.item.name }}</span>
      </span>
    </template>
  </v-autocomplete>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import { DEFI_MODULES } from '@/components/defi/wizard/consts';
import { SupportedModules } from '@/services/session/types';
import { SettingsUpdate } from '@/typing/types';

@Component({
  computed: {
    ...mapGetters('session', ['activeModules'])
  },
  methods: {
    ...mapActions('session', ['updateSettings'])
  }
})
export default class DefiModuleSelector extends Vue {
  updateSettings!: (update: SettingsUpdate) => Promise<void>;
  activeModules!: SupportedModules[];
  readonly supportedModules = DEFI_MODULES;
  selectedModules: SupportedModules[] = [];
  search: string = '';
  loading: boolean = false;

  mounted() {
    this.selectedModules = this.activeModules;
  }

  unselect(identifier: SupportedModules) {
    const selectionIndex = this.selectedModules.indexOf(identifier);
    if (selectionIndex < 0) {
      return;
    }
    this.selectedModules.splice(selectionIndex, 1);
  }

  async update(activeModules: SupportedModules[]) {
    this.loading = true;
    await this.updateSettings({ active_modules: activeModules });
    this.selectedModules = activeModules;
    this.loading = false;
  }
}
</script>
