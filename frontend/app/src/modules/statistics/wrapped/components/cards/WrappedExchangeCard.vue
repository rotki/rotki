<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import WrappedCard from '../WrappedCard.vue';

const { tradesByExchange } = defineProps<{
  tradesByExchange?: Record<string, BigNumber>;
}>();

const { t } = useI18n({ useScope: 'global' });

const exchangeItems = computed<Array<[string, BigNumber]>>(() => {
  if (!tradesByExchange)
    return [];
  return Object.entries(tradesByExchange).sort((a, b) => sortDesc(a[1], b[1]));
});

function weight(item: [string, BigNumber]): number {
  return item[1].toNumber();
}
</script>

<template>
  <WrappedCard
    v-if="exchangeItems.length > 0"
    :items="exchangeItems"
    :weight="weight"
  >
    <template #header-icon>
      <RuiIcon
        name="lu-coins-exchange"
        size="16"
      />
    </template>
    <template #header>
      {{ t('wrapped.exchange_activity') }}
    </template>
    <template #label="{ item }">
      <LocationDisplay
        horizontal
        class="[&_span]:text-rui-text!"
        :identifier="item[0]"
        size="20px"
      />
    </template>
    <template #value="{ item }">
      <ValueDisplay
        :value="item[1]"
        :format="{ integer: true }"
      />
      <span class="font-normal text-rui-text-secondary">{{ t('wrapped.unit.trades', item[1].toNumber()) }}</span>
    </template>
  </WrappedCard>
</template>
