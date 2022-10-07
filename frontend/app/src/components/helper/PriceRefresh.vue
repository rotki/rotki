<template>
  <v-btn
    outlined
    color="primary"
    :loading="refreshing"
    :disabled="disabled"
    @click="refresh"
  >
    <v-icon left>mdi-refresh</v-icon>
    {{ t('price_refresh.button') }}
  </v-btn>
</template>

<script setup lang="ts">
import { ComputedRef, PropType } from 'vue';
import { useSectionLoading } from '@/composables/common';
import { useBalancesStore } from '@/store/balances';
import { useAggregatedBalancesStore } from '@/store/balances/aggregated';
import { useTasks } from '@/store/tasks';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';

const props = defineProps({
  additionalAssets: {
    required: false,
    type: Array as PropType<string[]>,
    default: () => []
  }
});

const { isTaskRunning } = useTasks();
const { refreshPrices } = useBalancesStore();
const { isSectionRefreshing } = useSectionLoading();

const refreshing = isSectionRefreshing(Section.PRICES);

const loadingData = computed<boolean>(() => {
  return (
    get(isTaskRunning(TaskType.QUERY_BALANCES)) ||
    get(isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES)) ||
    get(isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES)) ||
    get(isTaskRunning(TaskType.MANUAL_BALANCES))
  );
});

const { assets } = useAggregatedBalancesStore();
const { additionalAssets } = toRefs(props);

const refresh = async () => {
  const additionals = get(additionalAssets);
  await refreshPrices(true, [...additionals, ...get(assets())]);
};

const { t } = useI18n();

const disabled: ComputedRef<boolean> = computed(() => {
  return get(refreshing) || get(loadingData);
});
</script>
