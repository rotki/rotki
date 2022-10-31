<template>
  <card full-height>
    <template #title>{{ t('kraken_staking_received.title') }}</template>
    <template #details>
      <v-btn-toggle v-model="current" dense mandatory>
        <v-btn :value="true">
          {{ t('kraken_staking_received.switch.current') }}
        </v-btn>
        <v-btn :value="false">
          {{ t('kraken_staking_received.switch.historical') }}
        </v-btn>
      </v-btn-toggle>
    </template>
    <div :class="$style.received">
      <v-row
        v-for="item in received"
        :key="item.asset"
        justify="space-between"
        no-gutters
        align="center"
      >
        <v-col cols="auto">
          <asset-details :asset="item.asset" dense />
        </v-col>
        <v-col cols="auto" :class="$style.amount">
          <value-accuracy-hint v-if="!current" />
          <balance-display
            no-icon
            :asset="item.asset"
            :value="getBalance(item)"
            :price-loading="pricesAreLoading && current"
          />
        </v-col>
      </v-row>
    </div>
  </card>
</template>

<script setup lang="ts">
import { Balance } from '@rotki/common';
import { PropType } from 'vue';
import ValueAccuracyHint from '@/components/helper/hint/ValueAccuracyHint.vue';
import { useBalancePricesStore } from '@/store/balances/prices';
import { ReceivedAmount } from '@/types/staking';
import { Zero } from '@/utils/bignumbers';

defineProps({
  received: {
    required: true,
    type: Array as PropType<ReceivedAmount[]>
  }
});

const { prices } = storeToRefs(useBalancePricesStore());
const current = ref(true);
const pricesAreLoading = computed(() => {
  return Object.keys(get(prices)).length === 0;
});
const getBalance = ({ amount, asset, usdValue }: ReceivedAmount): Balance => {
  const assetPrices = get(prices);

  const currentPrice = assetPrices[asset]
    ? assetPrices[asset].value.times(amount)
    : Zero;
  return {
    amount,
    usdValue: get(current) ? currentPrice : usdValue
  };
};

const { t } = useI18n();
</script>

<style lang="scss" module>
.received {
  max-height: 155px;
  overflow-y: scroll;
  overflow-x: hidden;
}

.amount {
  display: flex;
  flex-direction: row;
  flex-shrink: 1;
  align-items: center;
}
</style>
