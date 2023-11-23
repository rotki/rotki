<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';

const props = withDefaults(
  defineProps<{
    onlyChains?: Blockchain[];
  }>(),
  {
    onlyChains: () => []
  }
);

const { onlyChains } = toRefs(props);

const { t } = useI18n();

const { sortedQueryStatus, getKey } = useTransactionQueryStatus(onlyChains);
</script>

<template>
  <QueryStatusDialog :items="sortedQueryStatus" :get-key="getKey">
    <template #title>
      {{ t('transactions.query_status.title') }}
    </template>

    <template #current>
      <TransactionQueryStatusCurrent :only-chains="onlyChains" />
    </template>

    <template #item="{ item }">
      <AdaptiveWrapper>
        <EvmChainIcon :chain="item.evmChain" size="20px" />
      </AdaptiveWrapper>
      <TransactionQueryStatusLine :item="item" class="ms-2" />
    </template>

    <template #tooltip="{ item }">
      <i18n
        :path="
          item.period[0] === 0
            ? 'transactions.query_status.latest_period_end_date'
            : 'transactions.query_status.latest_period_date_range'
        "
      >
        <template #start>
          <DateDisplay :timestamp="item.period[0]" />
        </template>
        <template #end>
          <DateDisplay :timestamp="item.period[1]" />
        </template>
      </i18n>
    </template>

    <template #steps="{ item }">
      <TransactionQueryStatusSteps :item="item" />
    </template>
  </QueryStatusDialog>
</template>
