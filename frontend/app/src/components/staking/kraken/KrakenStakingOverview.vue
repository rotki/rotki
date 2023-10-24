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
  <RuiCard>
    <template #header>
      {{ t('kraken_staking_overview.title') }}
    </template>
    <div class="font-medium">
      {{ t('kraken_staking_overview.earned') }}
    </div>
    <div class="mt-2 ml-4 flex flex-col gap-2">
      <div class="flex justify-between items-center">
        <div class="flex items-center text-rui-text-secondary gap-2 font-light">
          {{ t('kraken_staking_overview.historical') }}
          <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
            <template #activator>
              <RuiIcon size="20" name="information-line" />
            </template>
            <span>{{ t('kraken_staking_overview.hint.historical') }}</span>
          </RuiTooltip>
        </div>
        <div class="flex items-center">
          <ValueAccuracyHint />
          <AmountDisplay
            show-currency="ticker"
            fiat-currency="USD"
            :value="totalUsd"
            class="text-rui-text-secondary"
          />
        </div>
      </div>
      <div class="flex justify-between items-center">
        <div class="flex items-center text-rui-text-secondary gap-2 font-light">
          {{ t('kraken_staking_overview.current') }}
          <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
            <template #activator>
              <RuiIcon size="20" name="information-line" />
            </template>
            <span>{{ t('kraken_staking_overview.hint.current') }}</span>
          </RuiTooltip>
        </div>
        <AmountDisplay
          show-currency="ticker"
          fiat-currency="USD"
          :loading="pricesAreLoading"
          :value="totalUsdCurrent"
          class="text-rui-text-secondary"
        />
      </div>
    </div>
  </RuiCard>
</template>
