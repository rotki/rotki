<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { useLocations } from '@/modules/core/common/use-locations';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import ListItem from '@/modules/shell/components/ListItem.vue';
import { Routes } from '@/router/routes';

interface ExchangeBoxProps {
  location: string;
  amount: BigNumber;
}

const { location } = defineProps<ExchangeBoxProps>();

const { getExchangeName } = useLocations();

const exchangeLocationRoute = computed<string>(() => {
  const route = Routes.BALANCES_EXCHANGE;
  return `${route}/${location}`;
});
</script>

<template>
  <RouterLink :to="exchangeLocationRoute">
    <ListItem
      :id="`${location}_box`"
      class="exchange-box__item group !py-1 px-6"
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
        {{ getExchangeName(location) }}
        <FiatDisplay
          :value="amount"
          class="font-medium"
        />
      </div>
    </ListItem>
  </RouterLink>
</template>
