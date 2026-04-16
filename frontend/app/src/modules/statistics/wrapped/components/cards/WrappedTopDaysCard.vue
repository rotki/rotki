<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import { useWrappedFormatters } from '../../use-wrapped-formatters';
import WrappedCard from '../WrappedCard.vue';

interface TopDay {
  timestamp: number;
  amount: BigNumber;
}

const { topDaysByNumberOfTransactions } = defineProps<{
  topDaysByNumberOfTransactions?: TopDay[];
}>();

const { t } = useI18n({ useScope: 'global' });
const { formatDate } = useWrappedFormatters();

const sortedDays = computed<TopDay[]>(() => {
  if (!topDaysByNumberOfTransactions)
    return [];
  return [...topDaysByNumberOfTransactions].sort((a, b) => sortDesc(a.amount, b.amount));
});
</script>

<template>
  <WrappedCard
    v-if="sortedDays.length > 0"
    :items="sortedDays"
  >
    <template #header-icon>
      <RuiIcon
        name="lu-calendar-days"
        class="text-rui-primary"
        size="12"
      />
    </template>
    <template #header>
      {{ t('wrapped.top_days') }}
    </template>
    <template #label="{ item, index }">
      <span>{{ index + 1 }}.</span>
      {{ formatDate(item.timestamp) }}
    </template>
    <template #value="{ item }">
      <ValueDisplay
        :value="item.amount"
        :format="{ integer: true }"
      />
      {{ t('explorers.tx') }}
    </template>
  </WrappedCard>
</template>
