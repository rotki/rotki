<script setup lang="ts">
import type { Balance } from '@rotki/common';
import type { ReceivedAmount } from '@/types/staking';

defineProps<{
  received: ReceivedAmount[];
}>();

const { prices } = storeToRefs(useBalancePricesStore());
const selection = ref<'current' | 'historical'>('current');
const pricesAreLoading = computed(() => Object.keys(get(prices)).length === 0);

function getBalance({ amount, asset, usdValue }: ReceivedAmount): Balance {
  const assetPrices = get(prices);

  const currentPrice = assetPrices[asset] ? assetPrices[asset].value.times(amount) : Zero;
  return {
    amount,
    usdValue: get(selection) === 'current' ? currentPrice : usdValue,
  };
}

const { t } = useI18n();
</script>

<template>
  <RuiCard
    no-padding
    class="mb-4"
  >
    <template #custom-header>
      <div class="flex items-center justify-between p-4">
        <h6 class="text-h6">
          {{ t('kraken_staking_received.title') }}
        </h6>
        <RuiButtonGroup
          v-model="selection"
          required
          variant="outlined"
          color="primary"
        >
          <RuiButton model-value="current">
            {{ t('kraken_staking_received.switch.current') }}
          </RuiButton>
          <RuiButton model-value="historical">
            {{ t('kraken_staking_received.switch.historical') }}
          </RuiButton>
        </RuiButtonGroup>
      </div>
    </template>
    <div class="p-4 py-0 max-h-[11rem]">
      <div
        v-for="item in received"
        :key="item.asset"
        class="flex items-center justify-between"
      >
        <AssetDetails
          :asset="item.asset"
          dense
        />
        <div class="flex items-center gap-3">
          <ValueAccuracyHint v-if="selection === 'historical'" />
          <BalanceDisplay
            no-icon
            :asset="item.asset"
            :value="getBalance(item)"
            :loading="pricesAreLoading && selection === 'current'"
          />
        </div>
      </div>
    </div>
  </RuiCard>
</template>
