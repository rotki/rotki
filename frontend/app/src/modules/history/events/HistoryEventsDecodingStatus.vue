<script lang="ts" setup>
import type { DataTableColumn } from '@rotki/ui-library';
import type { EvmUnDecodedTransactionsData, ProtocolCacheUpdatesData } from '@/modules/core/messaging/types';
import { toSentenceCase } from '@rotki/common';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import { useHistoryTransactionDecoding } from '@/modules/history/events/tx/use-history-transaction-decoding';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import { useProtocolCacheStatusStore } from '@/modules/history/use-protocol-cache-status-store';
import SuccessDisplay from '@/modules/shell/components/display/SuccessDisplay.vue';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface LocationData {
  evmChain: string;
  processed: number;
  total: number;
}

const { decodingStatus } = defineProps<{
  refreshing: boolean;
  decodingStatus: EvmUnDecodedTransactionsData[];
}>();

const emit = defineEmits<{
  'redecode-all-events': [];
  'reset-undecoded-transactions': [];
}>();

defineSlots<{
  default: () => any;
}>();

const { useIsActive } = useTaskCenter();
const fetching = useIsActive(ActivityKind.HISTORY_EVENTS, ActivityPart.UNDECODED);
// Transaction decoding runs native (Phase 2): aggregate liveness across every per-chain activity.
const isDecoding = useIsActive(ActivityKind.TX_DECODING);
const usedIsDecoding = useRefWithDebounce(isDecoding, 500);
// Transaction sync runs native (Phase 2): aggregate liveness across every {chain, address} activity.
const isTransactionsLoading = useIsActive(ActivityKind.TX_SYNC);

function redecodeAllEvents() {
  emit('redecode-all-events');
}

const { t } = useI18n({ useScope: 'global' });

const { checkMissingEventsAndRedecode } = useHistoryTransactionDecoding();

const { protocolCacheStatus, receivingProtocolCacheStatus } = storeToRefs(useProtocolCacheStatusStore());

function refresh() {
  if (decodingStatus.length === 0)
    emit('reset-undecoded-transactions');
}

const headers: DataTableColumn<LocationData>[] = [{
  align: 'center',
  cellClass: 'py-3',
  key: 'chain',
  label: t('common.location'),
}, {
  align: 'end',
  cellClass: '!pr-12',
  class: '!pr-12',
  key: 'number',
  label: t('transactions.events_decoding.undecoded_transactions'),
}, {
  align: 'center',
  key: 'progress',
  label: t('transactions.events_decoding.progress'),
}];

const total = computed<number>(() =>
  decodingStatus.reduce((sum, item) => sum + (item.total - item.processed), 0),
);

const [DefineProgress, ReuseProgress] = createReusableTemplate<{
  data: EvmUnDecodedTransactionsData & {
    protocolCacheRefreshStatus?: ProtocolCacheUpdatesData;
  };
}>();

watch(isDecoding, (loading) => {
  if (!loading) {
    refresh();
    emit('reset-undecoded-transactions');
  }
});

const combinedDecodingStatus = computed(() => {
  const data = [...decodingStatus].reverse();
  if (!get(receivingProtocolCacheStatus))
    return data;

  const last = get(protocolCacheStatus)[0];

  if (!last)
    return data;

  return [
    {
      chain: last.chain,
      processed: 0,
      protocolCacheRefreshStatus: last,
      total: 0,
    },
    ...data,
  ];
});

const allDone = computed(() => get(combinedDecodingStatus).every(status => status.total - status.processed === 0));

onMounted(() => refresh());
</script>

<template>
  <RuiCard>
    <template #custom-header>
      <div class="flex items-center justify-between gap-4 pt-3 p-4 pb-0">
        <h6 class="text-h6 text-rui-text">
          {{ t('transactions.events_decoding.title') }}
        </h6>
        <slot />
      </div>
    </template>

    <div class="mb-4">
      <div
        v-if="fetching || usedIsDecoding || isTransactionsLoading"
        class="flex items-center gap-4"
      >
        <RuiProgress
          color="primary"
          variant="indeterminate"
          circular
          size="20"
          thickness="3"
        />
        <template v-if="fetching">
          {{ t('transactions.events_decoding.fetching') }}
        </template>
        <template v-else-if="usedIsDecoding">
          {{ t('transactions.events_decoding.preparing') }}
        </template>
        <template v-else-if="isTransactionsLoading">
          {{ t('transactions.events_decoding.decoded.not_started') }}
        </template>
      </div>
      <div
        v-else-if="allDone"
        class="flex items-center gap-4"
      >
        <SuccessDisplay
          success
          size="28"
        />
        {{ t('transactions.events_decoding.decoded.true') }}
      </div>
      <div v-else>
        {{ t('transactions.events_decoding.decoded.false') }}
      </div>
    </div>

    <DefineProgress #default="{ data }">
      <div
        v-if="refreshing || usedIsDecoding"
        class="flex flex-col justify-center gap-3"
      >
        <RuiProgress
          class="max-w-[5rem] mx-auto"
          thickness="3"
          size="20"
          color="primary"
          :value="
            data.protocolCacheRefreshStatus
              ? (data.protocolCacheRefreshStatus.processed / (data.protocolCacheRefreshStatus.total || 1)) * 100
              : (data.processed / (data.total || 1)) * 100
          "
        />
        <i18n-t
          v-if="!data.protocolCacheRefreshStatus"
          scope="global"
          tag="span"
          keypath="transactions.events_decoding.transactions_processed"
        >
          <template #processed>
            {{ data.processed }}
          </template>
          <template #total>
            {{ data.total }}
          </template>
        </i18n-t>
        <i18n-t
          v-else
          scope="global"
          tag="span"
          keypath="transactions.protocol_cache_updates.protocol_pools_refreshed"
        >
          <template #protocol>
            {{ toSentenceCase(data.protocolCacheRefreshStatus.protocol) }}
          </template>
          <template #processed>
            {{ data.protocolCacheRefreshStatus.processed }}
          </template>
          <template #total>
            {{ data.protocolCacheRefreshStatus.total }}
          </template>
        </i18n-t>
      </div>
      <div v-else>
        -
      </div>
    </DefineProgress>

    <RuiDataTable
      v-if="combinedDecodingStatus.length > 0"
      :cols="headers"
      :rows="combinedDecodingStatus"
      dense
      row-attr="chain"
      striped
      outlined
    >
      <template #item.chain="{ row }">
        <LocationDisplay :identifier="row.chain" />
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

    <template #footer>
      <div class="grow" />
      <RuiButton
        v-if="total"
        color="primary"
        :disabled="refreshing || isDecoding"
        @click="checkMissingEventsAndRedecode()"
      >
        <template #prepend>
          <RuiIcon
            v-if="!isDecoding"
            name="lu-layout-list"
          />
          <RuiProgress
            v-else
            circular
            variant="indeterminate"
            size="18"
            thickness="3"
          />
        </template>
        {{ t('transactions.events_decoding.actions.redecode_missing_events') }}
      </RuiButton>
      <RuiButton
        color="error"
        :disabled="refreshing || isDecoding"
        @click="redecodeAllEvents()"
      >
        <template #prepend>
          <RuiIcon
            v-if="!isDecoding"
            name="lu-rotate-ccw"
          />
          <RuiProgress
            v-else
            circular
            variant="indeterminate"
            size="24"
            thickness="3"
          />
        </template>
        {{ t('transactions.events_decoding.redecode_all') }}
      </RuiButton>
    </template>
  </RuiCard>
</template>
