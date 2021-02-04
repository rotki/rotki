<template>
  <v-row class="mt-8">
    <v-col>
      <v-card>
        <v-card-title class="title">
          {{ $t('assets.price') }}
        </v-card-title>
        <v-card-text class="text-end text-h5 font-weight-medium">
          <amount-display
            class="pt-4"
            tooltip
            show-currency="symbol"
            fiat-currency="USD"
            :price-asset="identifier"
            :value="info.usdPrice"
          />
        </v-card-text>
      </v-card>
    </v-col>
    <v-col>
      <v-card>
        <v-card-title class="title">
          {{ $t('assets.amount') }}
        </v-card-title>
        <v-card-text class="text-end text-h5 font-weight-medium">
          <amount-display
            class="pt-4"
            :value="info.amount"
            :asset="identifier"
          />
        </v-card-text>
      </v-card>
    </v-col>
    <v-col>
      <v-card>
        <v-card-title class="title">
          {{ $t('assets.value') }}
        </v-card-title>
        <v-card-text class="text-end text-h5 font-weight-medium">
          <amount-display
            class="pt-4"
            show-currency="symbol"
            fiat-currency="USD"
            :amount="info.amount"
            :value="info.usdValue"
          />
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import { AssetPriceInfo } from '@/store/balances/types';

@Component({
  computed: {
    ...mapGetters('balances', ['assetPriceInfo'])
  }
})
export default class AssetValueRow extends Vue {
  @Prop({ required: true, type: String })
  identifier!: string;
  assetPriceInfo!: (asset: string) => AssetPriceInfo;

  get info(): AssetPriceInfo {
    return this.assetPriceInfo(this.identifier);
  }
}
</script>

<style scoped lang="scss">
.title {
  font-size: 14px;
  line-height: 17px;
  /* identical to box height */

  text-transform: uppercase;

  color: #447178;
}
</style>
