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

const { locationBreakdown: breakdown } = useBalancesBreakdown();
const locationBreakdown: ComputedRef<AssetBalanceWithPrice[]> = computed(() =>
  get(breakdown(get(identifier)))
);

const loadingData = computed<boolean>(
  () =>
    get(isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES)) ||
    get(isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES)) ||
    get(isTaskRunning(TaskType.QUERY_BALANCES))
);
</script>

<template>
  <Card v-if="loadingData || locationBreakdown.length > 0" outlined-body>
    <template #title> {{ t('common.assets') }} </template>
    <AssetBalances :loading="loadingData" :balances="locationBreakdown" />
  </Card>
</template>
