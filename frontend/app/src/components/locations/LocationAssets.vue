<script setup lang="ts">
import { type AssetBalanceWithPrice } from '@rotki/common';
import { type ComputedRef } from 'vue';
import { TaskType } from '@/types/task-type';

const props = defineProps({
  identifier: { required: true, type: String }
});

const { identifier } = toRefs(props);
const { isTaskRunning } = useTaskStore();

const { t } = useI18n();

const { locationBreakdown: breakdown } = useBalancesBreakdownStore();
const locationBreakdown: ComputedRef<AssetBalanceWithPrice[]> = computed(() => {
  return get(breakdown(get(identifier)));
});

const loadingData = computed<boolean>(() => {
  return (
    get(isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES)) ||
    get(isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES)) ||
    get(isTaskRunning(TaskType.QUERY_BALANCES))
  );
});
</script>
<template>
  <card v-if="loadingData || locationBreakdown.length > 0" outlined-body>
    <template #title> {{ t('common.assets') }} </template>
    <asset-balances :loading="loadingData" :balances="locationBreakdown" />
  </card>
</template>
