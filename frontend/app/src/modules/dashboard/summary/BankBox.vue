<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { useLocations } from '@/modules/core/common/use-locations';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import ListItem from '@/modules/shell/components/ListItem.vue';

const { location } = defineProps<{
  location: string;
  amount: BigNumber;
}>();

const { getExchangeName } = useLocations();
</script>

<template>
  <RouterLink :to="{ name: '/balances/banks/' }">
    <ListItem
      :id="`${location}_bank_box`"
      class="group !py-1 px-6"
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
