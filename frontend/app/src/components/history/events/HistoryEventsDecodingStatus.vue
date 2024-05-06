<script lang="ts" setup>
import { TaskType } from '@/types/task-type';
import type { EvmUnDecodedTransactionsData } from '@/types/websocket-messages';
import type { DataTableColumn } from '@rotki/ui-library-compat';

const props = defineProps<{
  refreshing: boolean;
  decodingStatus: EvmUnDecodedTransactionsData[];
}>();

const emit = defineEmits<{
  (e: 'redecode-all-events'): void;
  (e: 'reset-undecoded-transactions'): void;
}>();

const css = useCssModule();
const { isTaskRunning } = useTaskStore();
const fetching = isTaskRunning(TaskType.FETCH_UNDECODED_TXS);
const eventTaskLoading = isTaskRunning(TaskType.TRANSACTIONS_DECODING);
const partialEventTaskLoading = isTaskRunning(TaskType.TRANSACTIONS_DECODING, {
  all: false,
});
const allEventTaskLoading = isTaskRunning(TaskType.TRANSACTIONS_DECODING, {
  all: true,
});

function redecodeAllEvents() {
  emit('redecode-all-events');
}

const { t } = useI18n();

const { checkMissingEventsAndRedecode } = useHistoryTransactionDecoding();

function refresh() {
  if (props.decodingStatus.length === 0)
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
    label: t('transactions.events_decoding.undecoded_transactions'),
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

const total = computed<number>(() =>
  props.decodingStatus.reduce((sum, item) => sum + (item.total - item.processed), 0),
);

const [DefineProgress, ReuseProgress] = createReusableTemplate<{
  data: {
    evmChain: string;
    total: number;
    processed: number;
  };
}>();

watch(allEventTaskLoading, (loading) => {
  if (!loading) {
    refresh();
    emit('reset-undecoded-transactions');
  }
});

onMounted(() => refresh());
</script>

<template>
  <RuiCard>
    <template #custom-header>
      <div class="flex justify-between gap-4 p-4 pb-0">
        <h6 class="text-h6 text-rui-text">
          {{ t('transactions.events_decoding.title') }}
        </h6>
        <slot />
      </div>
    </template>

    <div
      v-if="decodingStatus.length > 0"
      :class="css.content"
    >
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
            path="transactions.events_decoding.transactions_processed"
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
        :rows="decodingStatus"
        dense
        row-attr="evmChain"
        striped
        outlined
      >
        <template #item.evmChain="{ row }">
          <LocationDisplay :identifier="row.evmChain" />
        </template>
        <template #item.number="{ row }">
          {{ row.total - row.processed }}
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
      <template v-if="fetching">
        {{ t('transactions.events_decoding.fetching') }}
      </template>
      <template v-else-if="eventTaskLoading">
        {{ t('transactions.events_decoding.preparing') }}
      </template>
      <template v-else>
        {{ t('transactions.events_decoding.decoded.true') }}
      </template>
    </div>

    <template #footer>
      <div class="grow" />
      <RuiButton
        v-if="total"
        color="primary"
        :disabled="refreshing || eventTaskLoading"
        @click="checkMissingEventsAndRedecode()"
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

<style module lang="scss">
.content {
  @apply overflow-y-auto -mx-4 px-4 -mt-2 pb-px;
  max-height: calc(90vh - 11.875rem);
  min-height: 50vh;
}
</style>
