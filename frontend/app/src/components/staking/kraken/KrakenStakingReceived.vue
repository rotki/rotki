<script setup lang="ts">
import { type Balance } from '@rotki/common';
import { type ReceivedAmount } from '@/types/staking';

defineProps<{
  received: ReceivedAmount[];
}>();

const { prices } = storeToRefs(useBalancePricesStore());
const current: Ref<boolean> = ref(true);
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
  <RuiCard>
    <template #custom-header>
      <div class="flex items-center justify-between p-4">
        <h5 class="text-h5">
          {{ t('kraken_staking_received.title') }}
        </h5>
        <RuiButtonGroup
          v-model="current"
          required
          variant="outlined"
          color="primary"
        >
          <template #default>
            <RuiButton :value="true">
              {{ t('kraken_staking_received.switch.current') }}
            </RuiButton>
            <RuiButton :value="false">
              {{ t('kraken_staking_received.switch.historical') }}
            </RuiButton>
          </template>
        </RuiButtonGroup>
      </div>
    </template>
    <div class="overflow-y-scroll pr-4 -mr-4 overflow-x-hidden max-h-[9rem]">
      <div
        v-for="item in received"
        :key="item.asset"
        class="flex items-center justify-between"
      >
        <AssetDetails :asset="item.asset" dense />
        <div class="flex items-center gap-3">
          <ValueAccuracyHint v-if="!current" />
          <BalanceDisplay
            no-icon
            :asset="item.asset"
            :value="getBalance(item)"
            :loading="pricesAreLoading && current"
          />
        </div>
      </div>
    </div>
  </RuiCard>
</template>
