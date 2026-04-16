<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { ProtocolCacheUpdatesData } from '@/modules/core/messaging/types';
import { useProtocolMetadata } from '@/modules/balances/protocols/use-protocol-metadata';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import { useProtocolCacheStatusStore } from '@/modules/history/use-protocol-cache-status-store';
import DefiIcon from '@/modules/settings/modules/DefiIcon.vue';
import SuccessDisplay from '@/modules/shell/components/display/SuccessDisplay.vue';

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

const protocolCacheStatusStore = useProtocolCacheStatusStore();
const { protocolCacheStatus, receivingProtocolCacheStatus } = storeToRefs(protocolCacheStatusStore);

const { useIsTaskRunning } = useTaskStore();
const taskRunning = useIsTaskRunning(TaskType.REFRESH_GENERAL_CACHE);

const { t } = useI18n({ useScope: 'global' });

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

const { findProtocolImage, findProtocolName, loading: metadataLoading } = useProtocolMetadata();

const dataWithInfo = computed<Data[]>(() =>
  get(protocolCacheStatus).map((item) => {
    const protocolImage = findProtocolImage(item.protocol);
    const protocolName = findProtocolName(item.protocol);

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
      class="overflow-y-auto -mx-4 px-4 -mt-2 pb-px max-h-[calc(90vh-11.875rem)] min-h-[50vh]"
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
            scope="global"
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
