<template>
  <v-row
    align="center"
    justify="end"
    no-gutters
    :class="
      $vuetify.breakpoint.mdAndUp && !$vuetify.breakpoint.mobile
        ? 'asset-movement-display--row'
        : null
    "
  >
    <v-col cols="auto">
      <balance-display
        :asset="movement.asset"
        :value="movement.value"
        :mode="gainLoss ? 'gain' : null"
      />
    </v-col>
    <v-col
      v-if="!gainLoss"
      sm="12"
      :md="$vuetify.breakpoint.mobile ? '12' : 'auto'"
      cols="12"
      :class="
        $vuetify.breakpoint.mdAndUp && !$vuetify.breakpoint.mobile
          ? 'mr-6'
          : null
      "
    >
      <v-icon
        v-if="$vuetify.breakpoint.mdAndUp && !$vuetify.breakpoint.mobile"
        color="grey"
      >
        mdi-chevron-right
      </v-icon>
      <v-icon v-else>mdi-chevron-down</v-icon>
    </v-col>
    <v-col cols="auto">
      <balance-display
        :asset="movement.toAsset"
        :value="movement.toValue"
        :mode="gainLoss ? 'loss' : null"
      />
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import { AssetMovement } from '@/components/display/types';

@Component({
  components: { BalanceDisplay }
})
export default class AssetMovementDisplay extends Vue {
  @Prop({ required: true, type: Object })
  movement!: AssetMovement;
  @Prop({ required: false, type: Boolean, default: false })
  gainLoss!: boolean;
}
</script>

<style scoped lang="scss">
.asset-movement-display {
  &--row {
    min-width: 380px;
  }
}
</style>
