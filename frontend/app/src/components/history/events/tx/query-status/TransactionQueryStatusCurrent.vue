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

const { queryingLength, length, isAllFinished } =
  useTransactionQueryStatus(onlyChains);
</script>

<template>
  <QueryStatusCurrent :finished="isAllFinished">
    <template #finished>
      {{ t('transactions.query_status.done_group', { length }) }}
    </template>

    <template #running>
      {{
        t('transactions.query_status.group', {
          length: queryingLength
        })
      }}
    </template>
  </QueryStatusCurrent>
</template>
