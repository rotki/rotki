<template>
  <v-select
    v-bind="rootAttrs"
    outlined
    persistent-hint
    item-value="identifier"
    item-text="identifier"
    :items="costBasisMethodData"
    v-on="rootListeners"
  >
    <template #item="{ item, attrs, on }">
      <v-list-item v-bind="attrs" v-on="on">
        <v-list-item-content>
          <v-list-item-title :class="$style.title">
            {{ item.identifier }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ item.label }}
          </v-list-item-subtitle>
        </v-list-item-content>
      </v-list-item>
    </template>
    <template #selection="{ item }">
      <span :class="$style.title">{{ item.identifier }}</span>
    </template>
  </v-select>
</template>

<script setup lang="ts">
import { useAttrs, useListeners } from 'vue';
import { useCostBasisMethod } from '@/store/reports/consts';

const rootAttrs = useAttrs();
const rootListeners = useListeners();
const { costBasisMethodData } = useCostBasisMethod();
</script>
<style module lang="scss">
.title {
  text-transform: uppercase;
  font-weight: 500;
}
</style>
