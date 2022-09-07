<template>
  <v-row>
    <v-col>
      <v-card>
        <v-card-title>
          <card-title>{{ t('common.price') }}</card-title>
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
          <card-title>{{ t('assets.amount') }}</card-title>
        </v-card-title>
        <v-card-text class="text-end text-h5 font-weight-medium">
          <amount-display class="pt-4" :value="info.amount" :asset="symbol" />
        </v-card-text>
      </v-card>
    </v-col>
    <v-col>
      <v-card>
        <v-card-title>
          <card-title>{{ t('assets.value') }}</card-title>
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
<script setup lang="ts">
import { get } from '@vueuse/core';
import { computed, toRefs } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import CardTitle from '@/components/typography/CardTitle.vue';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { AssetPriceInfo } from '@/store/balances/types';

const props = defineProps({
  identifier: { required: true, type: String },
  symbol: { required: true, type: String }
});
const { identifier } = toRefs(props);
const { assetPriceInfo } = useAssetInfoRetrieval();

const info = computed<AssetPriceInfo>(() => {
  return get(assetPriceInfo(get(identifier)));
});

const { t } = useI18n();
</script>
