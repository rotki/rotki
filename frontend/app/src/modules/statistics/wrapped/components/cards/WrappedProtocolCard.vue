<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import CounterpartyDisplay from '@/components/history/CounterpartyDisplay.vue';
import { sortDesc } from '@/utils/bignumbers';
import WrappedCard from '../WrappedCard.vue';

interface ProtocolActivity {
  protocol: string;
  transactions: BigNumber;
}

const props = defineProps<{
  transactionsPerProtocol?: ProtocolActivity[];
}>();

const { t } = useI18n({ useScope: 'global' });

const sortedProtocols = computed<ProtocolActivity[]>(() => {
  if (!props.transactionsPerProtocol)
    return [];
  return [...props.transactionsPerProtocol].sort((a, b) => sortDesc(a.transactions, b.transactions));
});
</script>

<template>
  <WrappedCard
    v-if="sortedProtocols.length > 0"
    :items="sortedProtocols"
  >
    <template #header-icon>
      <RuiIcon
        name="lu-blockchain"
        class="text-rui-primary"
        size="12"
      />
    </template>
    <template #header>
      {{ t('wrapped.protocol_activity') }}
    </template>
    <template #label="{ item, index }">
      <span>{{ index + 1 }}.</span>
      <CounterpartyDisplay :counterparty="item.protocol" />
    </template>
    <template #value="{ item }">
      <AmountDisplay
        :value="item.transactions"
        integer
      />
      {{ t('explorers.tx') }}
    </template>
  </WrappedCard>
</template>
