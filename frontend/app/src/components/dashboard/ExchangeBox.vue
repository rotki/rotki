<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { type TradeLocation } from '@/types/history/trade/location';
import { Routes } from '@/router/routes';

const props = defineProps<{
  location: TradeLocation;
  amount: BigNumber;
}>();

const { location } = toRefs(props);

const { exchangeName } = useLocations();

const exchangeLocationRoute = computed(() => {
  const route = Routes.ACCOUNTS_BALANCES_EXCHANGE;
  return `${route}/${get(location)}`;
});
</script>

<template>
  <VListItem
    :id="`${location}_box`"
    :to="exchangeLocationRoute"
    :ripple="false"
    class="exchange-box__item min-h-[2.25rem] group"
  >
    <VListItemAvatar tile class="grayscale group-hover:grayscale-0 m-0 mr-1">
      <LocationDisplay :identifier="location" icon size="30px" />
    </VListItemAvatar>
    <VListItemContent>
      <div class="flex flex-wrap justify-between gap-2">
        <span>
          {{ exchangeName(location) }}
        </span>
        <AmountDisplay
          show-currency="symbol"
          fiat-currency="USD"
          :value="amount"
        />
      </div>
    </VListItemContent>
  </VListItem>
</template>
