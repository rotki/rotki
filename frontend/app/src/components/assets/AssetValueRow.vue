<template>
  <v-row>
    <v-col>
      <v-card>
        <v-card-title>
          <card-title>{{ t('common.price') }}</card-title>
        </v-card-title>
        <v-card-text class="text-end text-h5 font-weight-medium pt-4">
          <amount-display
            v-if="info.usdPrice && info.usdPrice.gte(0)"
            show-currency="symbol"
            fiat-currency="USD"
            tooltip
            :price-asset="identifier"
            :value="info.usdPrice"
          />
          <div v-else class="pt-3 d-flex justify-end">
            <v-skeleton-loader height="20" width="70" type="text" />
          </div>
        </v-card-text>
      </v-card>
    </v-col>
    <v-col>
      <v-card>
        <v-card-title>
          <card-title>{{ t('assets.amount') }}</card-title>
        </v-card-title>
        <v-card-text class="text-end text-h5 font-weight-medium pt-4">
          <amount-display :value="info.amount" :asset="identifier" />
        </v-card-text>
      </v-card>
    </v-col>
    <v-col>
      <v-card>
        <v-card-title>
          <card-title>{{ t('assets.value') }}</card-title>
        </v-card-title>
        <v-card-text class="text-end text-h5 font-weight-medium pt-4">
          <amount-display
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
<script setup lang="ts">
import CardTitle from '@/components/typography/CardTitle.vue';
import { useAggregatedBalancesStore } from '@/store/balances/aggregated';
import { AssetPriceInfo } from '@/types/prices';

const props = defineProps({
  identifier: { required: true, type: String }
});
const { identifier } = toRefs(props);
const { assetPriceInfo } = useAggregatedBalancesStore();

const info = computed<AssetPriceInfo>(() => {
  return get(assetPriceInfo(identifier));
});

const { t } = useI18n();
</script>
