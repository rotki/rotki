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
        <v-avatar left class="d-flex">
          <adaptive-wrapper
            class="d-flex align-center"
            width="100%"
            height="100%"
          >
            <v-img
              width="26px"
              contain
              max-height="24px"
              :src="data.item.icon"
            />
          </adaptive-wrapper>
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

<script setup lang="ts">
import { onMounted, Ref, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { SUPPORTED_MODULES } from '@/components/defi/wizard/consts';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import { useBalancesStore } from '@/store/balances';
import { useSettingsStore } from '@/store/settings';
import { useGeneralSettingsStore } from '@/store/settings/general';
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

const supportedModules = SUPPORTED_MODULES;
const loading = ref(false);
const search = ref('');
const selectedModules: Ref<Module[]> = ref([]);
const autocomplete = ref();

const { activeModules } = storeToRefs(useGeneralSettingsStore());
const { update: updateSettings } = useSettingsStore();

const balancesStore = useBalancesStore();
const { nonFungibleBalancesState } = storeToRefs(balancesStore);
const { fetchNfBalances } = balancesStore;

const fetch = () => {
  const callback = () => fetchNfBalances({ ignoreCache: false });
  setTimeout(callback, 800);
};

const clearNfBalances = () => {
  const callback = () => set(nonFungibleBalancesState, {});
  setTimeout(callback, 800);
};

const onModuleActivation = (active: Module[]) => {
  if (wasActivated(active, get(selectedModules), Module.NFTS)) {
    fetch();
  }
};

const update = async (activeModules: Module[], clearSearch: boolean = true) => {
  if (clearSearch) {
    set(search, '');
    setTimeout(() => {
      const searchField = get(autocomplete) as any;
      if (searchField) {
        searchField.focus();
      }
    }, 10);
  }
  set(loading, true);

  await updateSettings({ activeModules });
  onModuleActivation(activeModules);
  set(selectedModules, activeModules);
  set(loading, false);
};

const unselect = (identifier: Module) => {
  const selected = get(selectedModules);
  const previouslyActive = [...selected];
  const selectionIndex = selected.indexOf(identifier);
  if (selectionIndex < 0) {
    return;
  }
  selected.splice(selectionIndex, 1);
  update(selected, false);

  if (wasDeactivated(selected, previouslyActive, Module.NFTS)) {
    clearNfBalances();
  }
};

onMounted(() => {
  set(selectedModules, get(activeModules));
});
</script>
