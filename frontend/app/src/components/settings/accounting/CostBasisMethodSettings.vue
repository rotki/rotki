<script setup lang="ts">
import { useListeners } from 'vue';

const rootAttrs = useAttrs();
const rootListeners = useListeners();
const { costBasisMethodData } = useCostBasisMethod();
</script>

<template>
  <VSelect
    v-bind="rootAttrs"
    outlined
    persistent-hint
    item-value="identifier"
    item-text="identifier"
    :items="costBasisMethodData"
    v-on="rootListeners"
  >
    <template #item="{ item, attrs, on }">
      <VListItem v-bind="attrs" v-on="on">
        <VListItemContent>
          <VListItemTitle :class="$style.title">
            {{ item.identifier }}
          </VListItemTitle>
          <VListItemSubtitle>
            {{ item.label }}
          </VListItemSubtitle>
        </VListItemContent>
      </VListItem>
    </template>
    <template #selection="{ item }">
      <span :class="$style.title">{{ item.identifier }}</span>
    </template>
  </VSelect>
</template>

<style module lang="scss">
.title {
  text-transform: uppercase;
  font-weight: 500;
}
</style>
