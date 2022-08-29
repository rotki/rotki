<template>
  <card v-if="loadingData || locationBreakdown.length > 0" outlined-body>
    <template #title> {{ t('common.assets') }} </template>
    <asset-balances :loading="loadingData" :balances="locationBreakdown" />
  </card>
</template>
<script setup lang="ts">
import { AssetBalanceWithPrice } from '@rotki/common';
import { get } from '@vueuse/core';
import { computed, toRefs } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import AssetBalances from '@/components/AssetBalances.vue';
import { useBalancesStore } from '@/store/balances';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

const props = defineProps({
  identifier: { required: true, type: String }
});

const { identifier } = toRefs(props);
const { isTaskRunning } = useTasks();

const { t } = useI18n();

const { locationBreakdown: breakdown } = useBalancesStore();
const locationBreakdown = computed<AssetBalanceWithPrice[]>(() => {
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
