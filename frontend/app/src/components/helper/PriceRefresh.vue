<template>
  <v-btn
    outlined
    color="primary"
    :loading="refreshing"
    :disabled="refreshing || loadingData"
    @click="refreshPrices({ ignoreCache: true })"
  >
    <v-icon left>mdi-refresh</v-icon>
    {{ $t('price_refresh.button') }}
  </v-btn>
</template>

<script lang="ts">
import { computed, defineComponent } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { setupStatusChecking } from '@/composables/common';
import { useBalancesStore } from '@/store/balances';
import { Section } from '@/store/const';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

export default defineComponent({
  name: 'PriceRefresh',
  setup() {
    const { isTaskRunning } = useTasks();
    const { refreshPrices } = useBalancesStore();
    const { isSectionRefreshing } = setupStatusChecking();

    const refreshing = isSectionRefreshing(Section.PRICES);

    const loadingData = computed<boolean>(() => {
      return (
        get(isTaskRunning(TaskType.QUERY_BALANCES)) ||
        get(isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES)) ||
        get(isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES)) ||
        get(isTaskRunning(TaskType.MANUAL_BALANCES))
      );
    });

    return { refreshing, loadingData, refreshPrices };
  }
});
</script>
