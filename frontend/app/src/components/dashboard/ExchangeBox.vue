<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { Routes } from '@/router/routes';

const props = defineProps<{
  location: string;
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
  <RouterLink :to="exchangeLocationRoute">
    <ListItem :id="`${location}_box`" class="exchange-box__item group py-1">
      <template #avatar>
        <div class="grayscale group-hover:grayscale-0">
          <LocationDisplay :identifier="location" icon size="30px" />
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
