<script lang="ts" setup>
import { type DataTableColumn } from '@rotki/ui-library-compat';
import { isEqual } from 'lodash-es';
import { TaskType } from '@/types/task-type';

defineProps<{
  refreshing: boolean;
}>();

const emit = defineEmits<{
  (e: 'redecode-all-evm-events'): void;
}>();

const { isTaskRunning } = useTaskStore();
const fetching = isTaskRunning(TaskType.EVM_UNDECODED_EVENTS);
const eventTaskLoading = isTaskRunning(TaskType.EVM_EVENTS_DECODING);
const partialEventTaskLoading = isTaskRunning(TaskType.EVM_EVENTS_DECODING, {
  all: false
});
const allEventTaskLoading = isTaskRunning(TaskType.EVM_EVENTS_DECODING, {
  all: true
});

const redecodeAllEvmEvents = () => {
  emit('redecode-all-evm-events');
};

const { t } = useI18n();

const {
  checkMissingTransactionEventsAndRedecode,
  unDecodedEventsBreakdown,
  fetchUndecodedEventsBreakdown
} = useHistoryTransactionDecoding();

const historyStore = useHistoryStore();
const { resetEvmUndecodedTransactionsStatus } = historyStore;
const { evmUndecodedTransactionsStatus } = storeToRefs(historyStore);

onMounted(() => refresh());

const refresh = async () => {
  await fetchUndecodedEventsBreakdown();

  if (Object.keys(get(unDecodedEventsBreakdown)).length === 0) {
    resetEvmUndecodedTransactionsStatus();
  }
};

const redecodeMissingEvents = async () => {
  await checkMissingTransactionEventsAndRedecode();
  await refresh();
};

const headers: DataTableColumn[] = [
  {
    label: t('common.location'),
    key: 'evmChain',
    align: 'center',
    cellClass: 'py-3'
  },
  {
    label: t('transactions.events_decoding.undecoded_events'),
    key: 'number',
    align: 'end',
    cellClass: '!pr-12',
    class: '!pr-12'
  },
  {
    label: t('transactions.events_decoding.progress'),
    key: 'progress',
    align: 'center'
  }
];

const locationsData = computed(() =>
  Object.entries(get(unDecodedEventsBreakdown)).map(([evmChain, number]) => {
    const progress = get(evmUndecodedTransactionsStatus)[evmChain];
    const total = progress?.total || number;

    return {
      evmChain,
      total,
      processed: progress?.processed || 0
    };
  })
);

const total: ComputedRef<number> = computed(() =>
  get(locationsData).reduce((sum, item) => sum + item.total, 0)
);

watch(eventTaskLoading, loading => {
  if (!loading) {
    refresh();
    resetEvmUndecodedTransactionsStatus();
  }
});

watch(evmUndecodedTransactionsStatus, (curr, prev) => {
  if (!isEqual(curr, prev)) {
    refresh();
  }
});

const [DefineProgress, ReuseProgress] = createReusableTemplate<{
  data: {
    evmChain: string;
    total: number;
    processed: number;
  };
}>();
</script>

<template>
  <RuiCard>
    <template #custom-header>
      <div class="flex justify-between gap-4 p-4 pb-0">
        <h5 class="text-h5">
          {{ t('transactions.events_decoding.title') }}
        </h5>
        <slot />
      </div>
    </template>

    <div v-if="locationsData.length > 0">
      <div class="mb-4">
        {{ t('transactions.events_decoding.decoded.false') }}
      </div>

      <DefineProgress #default="{ data }">
        <div
          v-if="refreshing || eventTaskLoading"
          class="flex flex-col justify-center gap-3"
        >
          <RuiProgress
            class="max-w-[5rem] mx-auto"
            thickness="2"
            size="20"
            color="primary"
            :value="(data.processed / data.total) * 100"
          />
          <i18n tag="span" path="transactions.events_decoding.events_processed">
            <template #processed>
              {{ data.processed }}
            </template>
            <template #total>
              {{ data.total }}
            </template>
          </i18n>
        </div>
        <div v-else>-</div>
      </DefineProgress>

      <RuiDataTable
        :cols="headers"
        :rows="locationsData"
        dense
        striped
        outlined
      >
        <template #item.evmChain="{ row }">
          <LocationDisplay :identifier="row.evmChain" />
        </template>
        <template #item.number="{ row }">
          {{ row.total }}
        </template>
        <template #item.progress="{ row }">
          <ReuseProgress :data="row" />
        </template>
        <template #tfoot>
          <tr>
            <th>{{ t('common.total') }}</th>
            <td class="text-end pr-12 py-2">{{ total }}</td>
          </tr>
        </template>
      </RuiDataTable>
    </div>
    <div v-else class="mb-4 flex items-center gap-4">
      <RuiProgress
        v-if="fetching || eventTaskLoading"
        color="primary"
        variant="indeterminate"
        circular
        size="28"
        thickness="2"
      />
      <SuccessDisplay v-else success size="28" />
      {{ t('transactions.events_decoding.decoded.true') }}
    </div>

    <template #footer>
      <div class="grow" />
      <RuiButton
        v-if="total"
        color="primary"
        :disabled="refreshing || eventTaskLoading"
        @click="redecodeMissingEvents()"
      >
        <template #prepend>
          <RuiIcon v-if="!partialEventTaskLoading" name="list-check-2" />
          <RuiProgress
            v-else
            circular
            variant="indeterminate"
            size="24"
            thickness="2"
          />
        </template>
        {{ t('transactions.events_decoding.actions.redecode_missing_events') }}
      </RuiButton>
      <RuiButton
        color="error"
        :disabled="refreshing || eventTaskLoading"
        @click="redecodeAllEvmEvents()"
      >
        <template #prepend>
          <RuiIcon v-if="!allEventTaskLoading" name="restart-line" />
          <RuiProgress
            v-else
            circular
            variant="indeterminate"
            size="24"
            thickness="2"
          />
        </template>
        {{ t('transactions.events_decoding.redecode_all') }}
      </RuiButton>
    </template>
  </RuiCard>
</template>
