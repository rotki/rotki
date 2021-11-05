<template>
  <v-row>
    <v-col>
      <v-card>
        <v-card-title>
          <card-title>{{ $t('assets.price') }}</card-title>
        </v-card-title>
        <v-card-text class="text-end text-h5 font-weight-medium">
          <amount-display
            class="pt-4"
            tooltip
            show-currency="symbol"
            fiat-currency="USD"
            :price-asset="symbol"
            :value="info.usdPrice"
          />
        </v-card-text>
      </v-card>
    </v-col>
    <v-col>
      <v-card>
        <v-card-title>
          <card-title>{{ $t('assets.amount') }}</card-title>
        </v-card-title>
        <v-card-text class="text-end text-h5 font-weight-medium">
          <amount-display class="pt-4" :value="info.amount" :asset="symbol" />
        </v-card-text>
      </v-card>
    </v-col>
    <v-col>
      <v-card>
        <v-card-title>
          <card-title>{{ $t('assets.value') }}</card-title>
        </v-card-title>
        <v-card-text class="text-end text-h5 font-weight-medium">
          <amount-display
            class="pt-4"
            show-currency="symbol"
            :fiat-currency="identifier"
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
import CardTitle from '@/components/typography/CardTitle.vue';
import { AssetPriceInfo } from '@/store/balances/types';

@Component({
  components: { CardTitle },
  computed: {
    ...mapGetters('balances', ['assetPriceInfo'])
  }
})
export default class AssetValueRow extends Vue {
  @Prop({ required: true, type: String })
  identifier!: string;
  @Prop({ required: true, type: String })
  symbol!: string;
  assetPriceInfo!: (asset: string) => AssetPriceInfo;

  get info(): AssetPriceInfo {
    return this.assetPriceInfo(this.identifier);
  }
}
</script>
