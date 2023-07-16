<script setup lang="ts">
import { type AssetMovement } from '@/types/defi';

withDefaults(
  defineProps<{
    movement: AssetMovement;
    gainLoss?: boolean;
  }>(),
  {
    gainLoss: false
  }
);

const { name: breakpoint, mobile } = useDisplay();
const small = computed(
  () => !(['xs', 'sm'].includes(get(breakpoint)) || get(mobile))
);
</script>

<template>
  <VRow
    align="center"
    justify="end"
    no-gutters
    :class="{
      [$style.row]: small
    }"
  >
    <VCol cols="auto">
      <BalanceDisplay
        :asset="movement.asset"
        :value="movement.value"
        :mode="gainLoss ? 'gain' : ''"
      />
    </VCol>
    <VCol
      v-if="!gainLoss"
      sm="12"
      :md="mobile ? '12' : 'auto'"
      cols="12"
      :class="small ? 'mr-6' : null"
    >
      <VIcon v-if="small" color="grey"> mdi-chevron-right </VIcon>
      <VIcon v-else>mdi-chevron-down</VIcon>
    </VCol>
    <VCol cols="auto">
      <BalanceDisplay
        :asset="movement.toAsset"
        :value="movement.toValue"
        :mode="gainLoss ? 'loss' : ''"
      />
    </VCol>
  </VRow>
</template>

<style module lang="scss">
.row {
  min-width: 380px;
}
</style>
