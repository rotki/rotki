<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { type BigNumber, toCapitalCase } from '@rotki/common';
import ListItem from '@/components/common/ListItem.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import { useLocations } from '@/composables/locations';
import { Routes } from '@/router/routes';

const props = defineProps<{
  name: string;
  amount: BigNumber;
}>();

const { name } = toRefs(props);

const manualBalancesRoute = computed<RouteLocationRaw>(() => ({
  path: `${Routes.BALANCES_MANUAL}/assets`,
  query: { location: get(name) },
}));

const { locationData } = useLocations();

const location = locationData(name);
</script>

<template>
  <RouterLink :to="manualBalancesRoute">
    <ListItem
      data-cy="manual-balance__summary"
      class="group !py-1 px-6"
      :data-location="name"
    >
      <template #avatar>
        <div class="grayscale group-hover:grayscale-0">
          <LocationDisplay
            :identifier="name"
            icon
            size="26px"
          />
        </div>
      </template>
      <div class="flex flex-wrap justify-between gap-1 text-rui-text">
        {{ location?.name || toCapitalCase(name) }}
        <AmountDisplay
          show-currency="symbol"
          force-currency
          :value="amount"
          class="font-medium"
        />
      </div>
    </ListItem>
  </RouterLink>
</template>
