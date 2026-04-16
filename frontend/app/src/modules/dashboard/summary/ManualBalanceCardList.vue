<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { type BigNumber, toCapitalCase } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { useLocations } from '@/modules/core/common/use-locations';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import ListItem from '@/modules/shell/components/ListItem.vue';
import { Routes } from '@/router/routes';

const { name, amount } = defineProps<{
  name: string;
  amount: BigNumber;
}>();

const manualBalancesRoute = computed<RouteLocationRaw>(() => ({
  path: `${Routes.BALANCES_MANUAL}/assets`,
  query: { location: name },
}));

const { useLocationData } = useLocations();

const location = useLocationData(() => name);
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
        <FiatDisplay
          :value="amount"
          class="font-medium"
        />
      </div>
    </ListItem>
  </RouterLink>
</template>
