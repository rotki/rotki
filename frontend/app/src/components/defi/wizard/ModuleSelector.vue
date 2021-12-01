<template>
  <v-autocomplete
    ref="autocomplete"
    :value="selectedModules"
    :search-input.sync="search"
    :items="supportedModules"
    hide-details
    hide-selected
    hide-no-data
    clearables
    multiple
    outlined
    chips
    :disabled="loading"
    :loading="loading"
    :open-on-clear="false"
    :label="$t('module_selector.label')"
    item-text="name"
    item-value="identifier"
    class="module-selector"
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
import { Component, Mixins } from 'vue-property-decorator';
import { SUPPORTED_MODULES } from '@/components/defi/wizard/consts';
import ModuleMixin from '@/mixins/module-mixin';
import { BalanceActions } from '@/store/balances/action-types';
import { BalanceMutations } from '@/store/balances/mutation-types';
import { Module } from '@/types/modules';

const wasActivated = (
  active: Module[],
  previouslyActive: Module[],
  module: Module
) => active.includes(module) && !previouslyActive.includes(module);

const wasDeactivated = (
  active: Module[],
  previouslyActive: Module[],
  module: Module
) => !active.includes(module) && previouslyActive.includes(module);

@Component({})
export default class ModuleSelector extends Mixins(ModuleMixin) {
  readonly supportedModules = SUPPORTED_MODULES;
  selectedModules: Module[] = [];
  search: string = '';
  loading: boolean = false;

  mounted() {
    this.selectedModules = this.activeModules;
  }

  unselect(identifier: Module) {
    const previouslyActive = [...this.selectedModules];
    const selectionIndex = this.selectedModules.indexOf(identifier);
    if (selectionIndex < 0) {
      return;
    }
    this.selectedModules.splice(selectionIndex, 1);
    this.update(this.selectedModules, false);

    if (wasDeactivated(this.selectedModules, previouslyActive, Module.NFTS)) {
      this.clearNfBalances();
    }
  }

  async update(activeModules: Module[], clearSearch: boolean = true) {
    if (clearSearch) {
      this.search = '';
      setTimeout(() => {
        const autocomplete = this.$refs.autocomplete as any;
        if (autocomplete) {
          autocomplete.focus();
        }
      }, 10);
    }
    this.loading = true;
    await this.activateModules(activeModules);
    this.onModuleActivation(activeModules);
    this.selectedModules = activeModules;
    this.loading = false;
  }

  private onModuleActivation(active: Module[]) {
    if (wasActivated(active, this.selectedModules, Module.NFTS)) {
      this.fetchNfBalances();
    }
  }

  private fetchNfBalances() {
    const callback = () =>
      this.$store
        .dispatch(`balances/${BalanceActions.FETCH_NF_BALANCES}`)
        .then();
    setTimeout(callback, 800);
  }

  private clearNfBalances() {
    const callback = () =>
      this.$store.commit(`balances/${BalanceMutations.UPDATE_NF_BALANCES}`, {});
    setTimeout(callback, 800);
  }
}
</script>
