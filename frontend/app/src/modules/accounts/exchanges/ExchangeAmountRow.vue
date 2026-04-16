<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { useLocations } from '@/modules/core/common/use-locations';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';

const { balance, exchange } = defineProps<{
  balance: BigNumber;
  exchange: string;
}>();

const { getExchangeName } = useLocations();

const name = computed<string>(() => {
  if (!exchange)
    return '';

  return getExchangeName(exchange);
});
</script>

<template>
  <div class="flex items-center gap-3 w-full">
    <LocationDisplay
      v-if="exchange"
      :open-details="false"
      :identifier="exchange"
      size="1.5rem"
      icon
    />
    <div class="flex gap-3 items-center justify-between w-full">
      <span class="text-sm">
        {{ name }}
      </span>
      <FiatDisplay
        :value="balance"
        class="text-rui-text-secondary text-xs"
      />
    </div>
  </div>
</template>
