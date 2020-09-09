<template>
  <v-row align="center" justify="end">
    <v-col class="d-flex flex-row" cols="auto">
      <crypto-icon :symbol="movement.asset" size="24px" />
      <div
        class="ml-2 d-flex flex-column align-end asset-movement-display__from"
      >
        <amount-display
          :asset="movement.asset"
          :asset-padding="assetPadding"
          :value="movement.value.amount"
          class="d-block font-weight-medium"
        />
        <amount-display
          fiat-currency="USD"
          :asset-padding="assetPadding"
          :value="movement.value.usdValue"
          class="d-block grey--text"
        />
      </div>
    </v-col>

    <v-col cols="auto">
      <v-icon large>mdi-chevron-right</v-icon>
    </v-col>
    <v-col class="d-flex flex-row" cols="auto">
      <crypto-icon :symbol="movement.toAsset" size="24px" />
      <div class="ml-2 d-flex flex-column align-end asset-movement-display__to">
        <amount-display
          :asset="movement.toAsset"
          :asset-padding="assetPadding"
          :value="movement.toValue.amount"
          class="d-block font-weight-medium"
        />
        <amount-display
          fiat-currency="USD"
          :asset-padding="assetPadding"
          :value="movement.toValue.usdValue"
          class="d-block grey--text"
        />
      </div>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import CryptoIcon from '@/components/CryptoIcon.vue';
import { AssetMovement } from '@/components/display/types';

@Component({
  components: { CryptoIcon }
})
export default class AssetMovementDisplay extends Vue {
  @Prop({ required: true })
  movement!: AssetMovement;

  assetPadding: number = 5;
}
</script>

<style scoped lang="scss">
.asset-movement-display {
  &__from {
    min-width: 16ch;
  }
  &__to {
    min-width: 16ch;
  }
}
</style>
