<script setup lang="ts">
import type { ProtocolCacheUpdatesData } from '@/types/websocket-messages';
import type { DataTableColumn } from '@rotki/ui-library';
import DefiIcon from '@/components/defi/DefiIcon.vue';
import SuccessDisplay from '@/components/display/SuccessDisplay.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import { useDefiMetadata } from '@/composables/defi/metadata';
import { useHistoryStore } from '@/store/history';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

type Data = ProtocolCacheUpdatesData & {
  key: string;
  protocolInfo: {
    name: string;
    icon?: string;
  };
};

defineProps<{
  refreshing: boolean;
}>();

defineSlots<{
  default: () => any;
}>();

const historyStore = useHistoryStore();
const { protocolCacheStatus, receivingProtocolCacheStatus } = storeToRefs(historyStore);

const { useIsTaskRunning } = useTaskStore();
const taskRunning = useIsTaskRunning(TaskType.REFRESH_GENERAL_CACHE);

const { t } = useI18n();

const headers: DataTableColumn<Data>[] = [{
  align: 'center',
  cellClass: 'py-3',
  key: 'chain',
  label: t('common.chain'),
}, {
  align: 'center',
  cellClass: 'py-3',
  key: 'protocol',
  label: t('common.protocol'),
}, {
  align: 'end',
  cellClass: '!pr-12',
  class: '!pr-12',
  key: 'number',
  label: t('transactions.protocol_cache_updates.outdated_data'),
}, {
  align: 'center',
  key: 'progress',
  label: t('transactions.events_decoding.progress'),
}];

const { getDefiImage, getDefiName, loading: metadataLoading } = useDefiMetadata();

const dataWithInfo = computed<Data[]>(() =>
  get(protocolCacheStatus).map((item) => {
    const protocolImage = get(getDefiImage(item.protocol));
    const protocolName = get(getDefiName(item.protocol));

    return {
      ...item,
      key: `${item.chain}#${item.protocol}`,
      protocolInfo: {
        icon: get(metadataLoading) ? undefined : protocolImage,
        name: protocolName,
      },
    };
  }),
);

const total = computed<number>(() =>
  get(protocolCacheStatus).reduce((sum, item) => sum + (item.total - item.processed), 0),
);

const [DefineProgress, ReuseProgress] = createReusableTemplate<{
  data: {
    chain: string;
    total: number;
    processed: number;
  };
}>();
</script>

<template>
  <RuiCard>
    <template #custom-header>
      <div class="flex justify-between gap-4 p-4 pb-0">
        <h6 class="text-h6 text-rui-text">
          {{ t('transactions.protocol_cache_updates.title') }}
        </h6>
        <slot />
      </div>
    </template>

    <div
      v-if="!receivingProtocolCacheStatus"
      class="mb-4 flex items-center gap-4"
    >
      <SuccessDisplay
        success
        size="28"
      />
      {{ t('transactions.protocol_cache_updates.no_ongoing') }}
    </div>
    <div
      v-else-if="protocolCacheStatus.length > 0"
      :class="$style.content"
    >
      <DefineProgress #default="{ data }">
        <div
          v-if="refreshing || taskRunning"
          class="flex flex-col justify-center gap-3"
        >
          <RuiProgress
            class="max-w-[5rem] mx-auto"
            thickness="2"
            size="20"
            color="primary"
            :value="(data.processed / data.total) * 100"
          />
          <i18n-t
            tag="span"
            keypath="transactions.protocol_cache_updates.pools_refreshed"
          >
            <template #processed>
              {{ data.processed }}
            </template>
            <template #total>
              {{ data.total }}
            </template>
          </i18n-t>
        </div>
        <div v-else>
          -
        </div>
      </DefineProgress>

      <RuiDataTable
        :cols="headers"
        :rows="dataWithInfo"
        dense
        row-attr="key"
        striped
        outlined
      >
        <template #item.chain="{ row }">
          <LocationDisplay :identifier="row.chain" />
        </template>
        <template #item.protocol="{ row }">
          <DefiIcon
            :item="row.protocolInfo"
            vertical
          />
        </template>
        <template #item.number="{ row }">
          {{ row.total - row.processed }}
        </template>
        <template #item.progress="{ row }">
          <ReuseProgress :data="row" />
        </template>
        <template #tfoot>
          <tr>
            <th colspan="2">
              {{ t('common.total') }}
            </th>
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
        color="primary"
        variant="indeterminate"
        circular
        size="28"
        thickness="2"
      />
      {{ t('transactions.protocol_cache_updates.refreshing') }}
    </div>
  </RuiCard>
</template>

<style module lang="scss">
.content {
  @apply overflow-y-auto -mx-4 px-4 -mt-2 pb-px;
  max-height: calc(90vh - 11.875rem);
  min-height: 50vh;
}
</style>
