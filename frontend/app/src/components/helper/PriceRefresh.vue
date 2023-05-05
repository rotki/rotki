<script setup lang="ts">
import { type ComputedRef, type PropType } from 'vue';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';

const props = defineProps({
  additionalAssets: {
    required: false,
    type: Array as PropType<string[]>,
    default: () => []
  }
});

const { isTaskRunning } = useTaskStore();
const { refreshPrices } = useBalances();
const { isLoading } = useStatusStore();

const refreshing = isLoading(Section.PRICES);

const loadingData = computed<boolean>(
  () =>
    get(isTaskRunning(TaskType.QUERY_BALANCES)) ||
    get(isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES)) ||
    get(isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES)) ||
    get(isTaskRunning(TaskType.MANUAL_BALANCES))
);

const { assets } = useAggregatedBalances();
const { additionalAssets } = toRefs(props);

const refresh = async () => {
  const additionals = get(additionalAssets);
  await refreshPrices(true, [...additionals, ...get(assets())]);
};

const { t } = useI18n();

const disabled: ComputedRef<boolean> = computed(
  () => get(refreshing) || get(loadingData)
);
</script>

<template>
  <v-btn
    outlined
    color="primary"
    :loading="refreshing"
    :disabled="disabled"
    @click="refresh()"
  >
    <v-icon left>mdi-refresh</v-icon>
    {{ t('price_refresh.button') }}
  </v-btn>
</template>
