<template>
  <card v-if="loadingData || locationBreakdown.length > 0" outlined-body>
    <template #title> {{ $t('common.assets') }} </template>
    <asset-balances :loading="loadingData" :balances="locationBreakdown" />
  </card>
</template>
<script lang="ts">
import { AssetBalanceWithPrice } from '@rotki/common';
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import AssetBalances from '@/components/AssetBalances.vue';
import { useBalancesStore } from '@/store/balances';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

export default defineComponent({
  name: 'LocationAssets',
  components: { AssetBalances },
  props: {
    identifier: { required: true, type: String }
  },
  setup(props) {
    const { identifier } = toRefs(props);
    const { isTaskRunning } = useTasks();

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

    return {
      locationBreakdown,
      loadingData
    };
  }
});
</script>
