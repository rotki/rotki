<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import { sortDesc } from '@/utils/bignumbers';
import WrappedCard from '../WrappedCard.vue';

const props = defineProps<{
  tradesByExchange?: Record<string, BigNumber>;
}>();

const { t } = useI18n({ useScope: 'global' });

const exchangeItems = computed<Array<[string, BigNumber]>>(() => {
  if (!props.tradesByExchange)
    return [];
  return Object.entries(props.tradesByExchange).sort((a, b) => sortDesc(a[1], b[1]));
});
</script>

<template>
  <WrappedCard
    v-if="exchangeItems.length > 0"
    :items="exchangeItems"
  >
    <template #header-icon>
      <RuiIcon
        name="lu-coins-exchange"
        class="text-rui-primary"
        size="12"
      />
    </template>
    <template #header>
      {{ t('wrapped.exchange_activity') }}
    </template>
    <template #label="{ item, index }">
      <span>{{ index + 1 }}.</span>
      <LocationDisplay
        horizontal
        class="[&_span]:!text-rui-text"
        :identifier="item[0]"
        size="20px"
      />
    </template>
    <template #value="{ item }">
      <AmountDisplay
        :value="item[1]"
        integer
      />
      {{ t('common.trades', item[1].toNumber()) }}
    </template>
  </WrappedCard>
</template>
