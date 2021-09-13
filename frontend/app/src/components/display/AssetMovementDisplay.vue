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

<script lang="ts">
import { computed, defineComponent, PropType } from '@vue/composition-api';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import { AssetMovement } from '@/components/display/types';
import { setupThemeCheck } from '@/composables/common';

export default defineComponent({
  components: { BalanceDisplay },
  props: {
    movement: { required: true, type: Object as PropType<AssetMovement> },
    gainLoss: { required: false, type: Boolean, default: false }
  },
  setup() {
    const { breakpoint, isMobile } = setupThemeCheck();
    const small = computed(
      () => !(['xs', 'sm'].includes(breakpoint.value) || isMobile.value)
    );
    return {
      small,
      isMobile
    };
  }
});
</script>

<style module lang="scss">
.row {
  min-width: 380px;
}
</style>
