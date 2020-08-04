<template>
  <v-autocomplete
    :value="value"
    :search-input.sync="search"
    :items="supportedModules"
    hide-details
    hide-selected
    hide-no-data
    clearables
    multiple
    chips
    :open-on-clear="false"
    label="Select modules(s)"
    item-text="name"
    item-value="identifier"
    class="defi-module-selector"
    @input="input"
  >
    <template #selection="data">
      <v-chip close pill @click:close="unselect(data.item.identifier)">
        <span class="d-flex flex-row align-center">
          <v-img width="55px" contain max-height="24px" :src="data.item.icon" />
          <span v-if="data.item.displayName"> {{ data.item.displayName }}</span>
        </span>
      </v-chip>
    </template>
    <template #item="data">
      <span v-bind="data.attrs" class="d-flex flex-row align-center">
        <v-img
          width="55px"
          contain
          position="left"
          max-height="24px"
          :src="data.item.icon"
        />
        <span v-if="data.item.displayName"> {{ data.item.displayName }}</span>
      </span>
    </template>
  </v-autocomplete>
</template>

<script lang="ts">
import { Component, Vue, Emit, Prop } from 'vue-property-decorator';
import { DEFI_MODULES } from '@/components/defi/wizard/consts';
import { SupportedModules } from '@/services/session/types';

@Component({})
export default class DefiProtocolSelector extends Vue {
  @Prop({ required: true })
  value!: SupportedModules[];

  readonly supportedModules = DEFI_MODULES;

  search: string = '';

  unselect(identifier: SupportedModules) {
    const selectionIndex = this.value.indexOf(identifier);
    if (selectionIndex < 0) {
      return;
    }
    this.value.splice(selectionIndex, 1);
  }

  @Emit()
  input(_activeModules: string[]) {}
}
</script>

<style scoped lang="scss"></style>
