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
</script>

<template>
  <div class="flex gap-3 items-center justify-end">
    <BalanceDisplay
      :asset="movement.asset"
      :value="movement.value"
      :mode="gainLoss ? 'gain' : ''"
    />
    <div v-if="!gainLoss">
      <RuiIcon name="arrow-down-s-line" />
    </div>
    <BalanceDisplay
      :asset="movement.toAsset"
      :value="movement.toValue"
      :mode="gainLoss ? 'loss' : ''"
    />
  </div>
</template>

<style module lang="scss">
.row {
  min-width: 380px;
}
</style>
