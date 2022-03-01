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
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import CardTitle from '@/components/typography/CardTitle.vue';
import { useAssetInfoRetrieval } from '@/store/assets';
import { AssetPriceInfo } from '@/store/balances/types';

export default defineComponent({
  name: 'AssetValueRow',
  components: { CardTitle },
  props: {
    identifier: { required: true, type: String },
    symbol: { required: true, type: String }
  },
  setup(props) {
    const { identifier } = toRefs(props);
    const { assetPriceInfo } = useAssetInfoRetrieval();

    const info = computed<AssetPriceInfo>(() => {
      return get(assetPriceInfo(get(identifier)));
    });

    return { info };
  }
});
</script>
