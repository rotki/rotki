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
  <query-status-dialog :items="sortedQueryStatus" :get-key="getKey">
    <template #title>
      {{ t('transactions.query_status.title') }}
    </template>

    <template #current>
      <transaction-query-status-current
        :only-chains="onlyChains"
        class="px-6 pb-4 text-caption"
      />
    </template>

    <template #item="{ item }">
      <adaptive-wrapper>
        <evm-chain-icon :chain="item.evmChain" size="20px" />
      </adaptive-wrapper>
      <transaction-query-status-line :item="item" class="ms-2" />
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
          <date-display :timestamp="item.period[0]" />
        </template>
        <template #end>
          <date-display :timestamp="item.period[1]" />
        </template>
      </i18n>
    </template>

    <template #steps="{ item }">
      <transaction-query-status-steps :item="item" />
    </template>
  </query-status-dialog>
</template>
