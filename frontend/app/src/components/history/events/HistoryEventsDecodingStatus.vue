<script lang="ts" setup>
import { isEqual } from 'lodash-es';
import { TaskType } from '@/types/task-type';
import { TransactionChainType } from '@/types/history/events';
import type { EvmUnDecodedTransactionsData } from '@/types/websocket-messages';
import type { DataTableColumn } from '@rotki/ui-library-compat';

const props = defineProps<{
  refreshing: boolean;
  locationsData: EvmUnDecodedTransactionsData[];
  unDecodedTransactionsStatus: Record<string, EvmUnDecodedTransactionsData>;
}>();

const emit = defineEmits<{
  (e: 'redecode-all-events'): void;
  (e: 'reset-undecoded-transactions'): void;
}>();

const { isTaskRunning } = useTaskStore();
const fetching = isTaskRunning(TaskType.FETCH_UNDECODED_EVENTS);
const eventTaskLoading = isTaskRunning(TaskType.EVENTS_ENCODING);
const partialEventTaskLoading = isTaskRunning(TaskType.EVENTS_ENCODING, {
  all: false,
});
const allEventTaskLoading = isTaskRunning(TaskType.EVENTS_ENCODING, {
  all: true,
});

function redecodeAllEvents() {
  emit('redecode-all-events');
}

const { t } = useI18n();

const {
  checkMissingEventsAndReDecode,
  fetchUnDecodedEventsBreakdown,
} = useHistoryTransactionDecoding();

onMounted(() => refresh());

async function refresh() {
  await fetchUnDecodedEventsBreakdown(TransactionChainType.EVM);
  await fetchUnDecodedEventsBreakdown(TransactionChainType.EVMLIKE);

  if (props.locationsData.length === 0)
    emit('reset-undecoded-transactions');
}

const headers: DataTableColumn[] = [
  {
    label: t('common.location'),
    key: 'evmChain',
    align: 'center',
    cellClass: 'py-3',
  },
  {
    label: t('transactions.events_decoding.undecoded_events'),
    key: 'number',
    align: 'end',
    cellClass: '!pr-12',
    class: '!pr-12',
  },
  {
    label: t('transactions.events_decoding.progress'),
    key: 'progress',
    align: 'center',
  },
];

const total: ComputedRef<number> = computed(() =>
  props.locationsData.reduce((sum, item) => sum + item.total, 0),
);

watch(eventTaskLoading, (loading) => {
  if (!loading) {
    refresh();
    emit('reset-undecoded-transactions');
  }
});

watch(toRef(props, 'unDecodedTransactionsStatus'), (curr, prev) => {
  if (!isEqual(curr, prev))
    refresh();
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
        <h5 class="text-h6">
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
          <i18n
            tag="span"
            path="transactions.events_decoding.events_processed"
          >
            <template #processed>
              {{ data.processed }}
            </template>
            <template #total>
              {{ data.total }}
            </template>
          </i18n>
        </div>
        <div v-else>
          -
        </div>
      </DefineProgress>

      <RuiDataTable
        :cols="headers"
        :rows="locationsData"
        dense
        row-attr="evmChain"
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
            <td class="text-end pr-12 py-2">
              {{ total }}
            </td>
          </tr>
        </template>
      </RuiDataTable>
    </div>
    <div
      v-else
      class="mb-4 flex items-center gap-4"
    >
      <RuiProgress
        v-if="fetching || eventTaskLoading"
        color="primary"
        variant="indeterminate"
        circular
        size="28"
        thickness="2"
      />
      <SuccessDisplay
        v-else
        success
        size="28"
      />
      {{ t('transactions.events_decoding.decoded.true') }}
    </div>

    <template #footer>
      <div class="grow" />
      <RuiButton
        v-if="total"
        color="primary"
        :disabled="refreshing || eventTaskLoading"
        @click="checkMissingEventsAndReDecode()"
      >
        <template #prepend>
          <RuiIcon
            v-if="!partialEventTaskLoading"
            name="list-check-2"
          />
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
        @click="redecodeAllEvents()"
      >
        <template #prepend>
          <RuiIcon
            v-if="!allEventTaskLoading"
            name="restart-line"
          />
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
