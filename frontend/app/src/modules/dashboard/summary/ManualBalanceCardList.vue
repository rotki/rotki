<script setup lang="ts">
import { Routes } from '@/router/routes';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useLocations } from '@/composables/locations';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import ListItem from '@/components/common/ListItem.vue';
import type { BigNumber } from '@rotki/common';

const props = defineProps<{
  name: string;
  amount: BigNumber;
}>();

const manualBalancesRoute = Routes.BALANCES_MANUAL;

const { name } = toRefs(props);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { locationData } = useLocations();

const location = locationData(name);
</script>

<template>
  <RouterLink :to="manualBalancesRoute">
    <ListItem
      data-cy="manual-balance__summary"
      class="group py-1 px-6"
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
          :fiat-currency="currencySymbol"
          :value="amount"
          class="font-medium"
        />
      </div>
    </ListItem>
  </RouterLink>
</template>
