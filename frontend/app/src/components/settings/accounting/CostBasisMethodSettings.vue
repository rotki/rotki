<template>
  <v-select
    v-bind="$attrs"
    outlined
    persistent-hint
    item-value="identifier"
    item-text="identifier"
    :items="selections"
    v-on="$listeners"
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

<script lang="ts">
import { defineComponent } from 'vue';
import { costBasisMethodData } from '@/store/reports/consts';
export default defineComponent({
  name: 'CostBasisMethodSettings',
  setup() {
    return {
      selections: costBasisMethodData
    };
  }
});
</script>
<style module lang="scss">
.title {
  text-transform: uppercase;
  font-weight: 500;
}
</style>
