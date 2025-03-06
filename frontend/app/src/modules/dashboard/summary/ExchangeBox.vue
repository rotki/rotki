<script setup lang="ts">
import { Routes } from '@/router/routes';
import { useLocations } from '@/composables/locations';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import ListItem from '@/components/common/ListItem.vue';
import type { BigNumber } from '@rotki/common';

interface ExchangeBoxProps {
  location: string;
  amount: BigNumber;
}

const props = defineProps<ExchangeBoxProps>();

const { exchangeName } = useLocations();

const exchangeLocationRoute = computed<string>(() => {
  const route = Routes.BALANCES_EXCHANGE;
  return `${route}/${props.location}`;
});
</script>

<template>
  <RouterLink :to="exchangeLocationRoute">
    <ListItem
      :id="`${location}_box`"
      class="exchange-box__item group py-1 px-6"
    >
      <template #avatar>
        <div class="grayscale group-hover:grayscale-0">
          <LocationDisplay
            :identifier="location"
            icon
            size="26px"
          />
        </div>
      </template>
      <div class="flex flex-wrap justify-between gap-1 text-rui-text">
        {{ exchangeName(location) }}
        <AmountDisplay
          show-currency="symbol"
          fiat-currency="USD"
          :value="amount"
          class="font-medium"
        />
      </div>
    </ListItem>
  </RouterLink>
</template>
