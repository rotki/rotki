<script setup lang="ts">
import { type Balance } from '@rotki/common';
import { type ReceivedAmount } from '@/types/staking';

defineProps<{
  received: ReceivedAmount[];
}>();

const { prices } = storeToRefs(useBalancePricesStore());
const current = ref(true);
const pricesAreLoading = computed(() => Object.keys(get(prices)).length === 0);
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

<template>
  <Card full-height>
    <template #title>{{ t('kraken_staking_received.title') }}</template>
    <template #details>
      <VBtnToggle v-model="current" dense mandatory>
        <VBtn :value="true">
          {{ t('kraken_staking_received.switch.current') }}
        </VBtn>
        <VBtn :value="false">
          {{ t('kraken_staking_received.switch.historical') }}
        </VBtn>
      </VBtnToggle>
    </template>
    <div :class="$style.received">
      <VRow
        v-for="item in received"
        :key="item.asset"
        justify="space-between"
        no-gutters
        align="center"
      >
        <VCol cols="auto">
          <AssetDetails :asset="item.asset" dense />
        </VCol>
        <VCol cols="auto" :class="$style.amount">
          <ValueAccuracyHint v-if="!current" />
          <BalanceDisplay
            no-icon
            :asset="item.asset"
            :value="getBalance(item)"
            :loading="pricesAreLoading && current"
          />
        </VCol>
      </VRow>
    </div>
  </Card>
</template>

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
