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
  <v-row
    align="center"
    justify="end"
    no-gutters
    :class="{
      [$style.row]: small
    }"
  >
    <v-col cols="auto">
      <balance-display
        :asset="movement.asset"
        :value="movement.value"
        :mode="gainLoss ? 'gain' : ''"
      />
    </v-col>
    <v-col
      v-if="!gainLoss"
      sm="12"
      :md="mobile ? '12' : 'auto'"
      cols="12"
      :class="small ? 'mr-6' : null"
    >
      <v-icon v-if="small" color="grey"> mdi-chevron-right </v-icon>
      <v-icon v-else>mdi-chevron-down</v-icon>
    </v-col>
    <v-col cols="auto">
      <balance-display
        :asset="movement.toAsset"
        :value="movement.toValue"
        :mode="gainLoss ? 'loss' : ''"
      />
    </v-col>
  </v-row>
</template>

<style module lang="scss">
.row {
  min-width: 380px;
}
</style>
