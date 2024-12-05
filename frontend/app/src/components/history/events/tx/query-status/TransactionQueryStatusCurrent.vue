<script setup lang="ts">
import { useTransactionQueryStatus } from '@/composables/history/events/query-status/tx-query-status';
import type { Blockchain } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    onlyChains?: Blockchain[];
  }>(),
  {
    onlyChains: () => [],
  },
);

const { onlyChains } = toRefs(props);

const { t } = useI18n();

const { isAllFinished, length, queryingLength } = useTransactionQueryStatus(onlyChains);
</script>

<template>
  <HistoryQueryStatusCurrent :finished="isAllFinished">
    <template #finished>
      {{ t('transactions.query_status.done_group', length) }}
    </template>

    <template #running>
      {{ t('transactions.query_status.group', queryingLength) }}
    </template>
  </HistoryQueryStatusCurrent>
</template>
