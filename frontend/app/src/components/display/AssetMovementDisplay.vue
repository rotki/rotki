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
      :md="isMobile ? '12' : 'auto'"
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

<script setup lang="ts">
import { PropType } from 'vue';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import { useTheme } from '@/composables/common';
import { AssetMovement } from '@/types/defi';

defineProps({
  movement: { required: true, type: Object as PropType<AssetMovement> },
  gainLoss: { required: false, type: Boolean, default: false }
});

const { breakpoint, isMobile } = useTheme();
const small = computed(
  () => !(['xs', 'sm'].includes(get(breakpoint)) || get(isMobile))
);
</script>

<style module lang="scss">
.row {
  min-width: 380px;
}
</style>
