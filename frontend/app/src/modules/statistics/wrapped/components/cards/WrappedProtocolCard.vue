<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';
import WrappedCard from '../WrappedCard.vue';

interface ProtocolActivity {
  protocol: string;
  transactions: BigNumber;
}

const { transactionsPerProtocol } = defineProps<{
  transactionsPerProtocol?: ProtocolActivity[];
}>();

const { t } = useI18n({ useScope: 'global' });

const sortedProtocols = computed<ProtocolActivity[]>(() => {
  if (!transactionsPerProtocol)
    return [];
  return [...transactionsPerProtocol].sort((a, b) => sortDesc(a.transactions, b.transactions));
});

function weight(activity: ProtocolActivity): number {
  return activity.transactions.toNumber();
}
</script>

<template>
  <WrappedCard
    v-if="sortedProtocols.length > 0"
    :items="sortedProtocols"
    :weight="weight"
  >
    <template #header-icon>
      <RuiIcon
        name="lu-blockchain"
        size="16"
      />
    </template>
    <template #header>
      {{ t('wrapped.protocol_activity') }}
    </template>
    <template #label="{ item }">
      <CounterpartyDisplay :counterparty="item.protocol" />
    </template>
    <template #value="{ item }">
      <ValueDisplay
        :value="item.transactions"
        :format="{ integer: true }"
      />
      <span class="font-normal text-rui-text-secondary">{{ t('wrapped.unit.transactions', item.transactions.toNumber()) }}</span>
    </template>
  </WrappedCard>
</template>
