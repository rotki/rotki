<template>
  <card v-if="loadingData || locationBreakdown.length > 0" outlined-body>
    <template #title> {{ $t('locations.assets') }} </template>
    <asset-balances :loading="loadingData" :balances="locationBreakdown" />
  </card>
</template>
<script lang="ts">
import { AssetBalanceWithPrice } from '@rotki/common';
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import AssetBalances from '@/components/AssetBalances.vue';
import { useTasks } from '@/store/tasks';
import { useStore } from '@/store/utils';
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

    const store = useStore();
    const locationBreakdown = computed<AssetBalanceWithPrice[]>(() => {
      return store.getters['balances/locationBreakdown'](identifier.value);
    });

    const loadingData = computed<boolean>(() => {
      return (
        isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES).value ||
        isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES).value ||
        isTaskRunning(TaskType.QUERY_BALANCES).value
      );
    });

    return {
      locationBreakdown,
      loadingData
    };
  }
});
</script>
