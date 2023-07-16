<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { type ReceivedAmount } from '@/types/staking';

const props = defineProps<{
  totalUsd: BigNumber;
  earned: ReceivedAmount[];
}>();

const { earned } = toRefs(props);
const { prices } = storeToRefs(useBalancePricesStore());
const pricesAreLoading = computed(() => {
  const assetPrices = get(prices);
  return Object.keys(assetPrices).length === 0;
});
const totalUsdCurrent = computed<BigNumber>(() => {
  const earnedAssets = get(earned);
  const assetPrices = get(prices);
  if (Object.keys(assetPrices).length === 0) {
    return Zero;
  }

  let sum = Zero;

  for (const { asset, amount } of earnedAssets) {
    const assetPrice = assetPrices[asset];
    assert(assetPrice);
    sum = sum.plus(assetPrice.value.times(amount));
  }
  return sum;
});

const { t } = useI18n();
</script>

<template>
  <Card full-height>
    <template #title>{{ t('kraken_staking_overview.title') }}</template>
    <VRow class="pt-1 pb-4">
      <VCol>
        <VRow no-gutters>
          <VCol>
            <div class="font-weight-medium">
              {{ t('kraken_staking_overview.earned') }}
            </div>
          </VCol>
        </VRow>
        <VRow justify="space-between" align="center" no-gutters class="mt-2">
          <VCol cols="auto">
            <div
              class="d-flex align-center text--secondary font-weight-light ms-2"
            >
              {{ t('kraken_staking_overview.historical') }}
              <VTooltip open-delay="400" top>
                <template #activator="{ attrs, on }">
                  <VIcon class="ms-1" small v-bind="attrs" v-on="on">
                    mdi-information
                  </VIcon>
                </template>
                <span>{{ t('kraken_staking_overview.hint.historical') }}</span>
              </VTooltip>
            </div>
          </VCol>
          <VCol cols="auto">
            <div class="d-flex align-center">
              <ValueAccuracyHint />
              <AmountDisplay
                show-currency="ticker"
                fiat-currency="USD"
                :value="totalUsd"
                class="grey--text"
              />
            </div>
          </VCol>
        </VRow>
        <VRow justify="space-between" align="center" no-gutters class="mt-2">
          <VCol cols="auto">
            <div
              class="d-flex align-center text--secondary font-weight-light ms-2"
            >
              {{ t('kraken_staking_overview.current') }}
              <VTooltip open-delay="400" top>
                <template #activator="{ attrs, on }">
                  <VIcon class="ms-1" small v-bind="attrs" v-on="on">
                    mdi-information
                  </VIcon>
                </template>
                <span>{{ t('kraken_staking_overview.hint.current') }}</span>
              </VTooltip>
            </div>
          </VCol>
          <VCol cols="auto">
            <AmountDisplay
              show-currency="ticker"
              fiat-currency="USD"
              :loading="pricesAreLoading"
              :value="totalUsdCurrent"
              class="grey--text"
            />
          </VCol>
        </VRow>
      </VCol>
    </VRow>
  </Card>
</template>
