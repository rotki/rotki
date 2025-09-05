<script setup lang="ts">
import type { CommonQueryProgressData, HistoryQueryProgressType } from '@/modules/dashboard/history-progress/types';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import HashLink from '@/modules/common/links/HashLink.vue';

interface HistoryQueryProgressOperationData {
  type?: HistoryQueryProgressType;
  status?: string;
  chain?: string;
  address?: string;
  location?: string;
  name?: string;
}

interface Props {
  progress: CommonQueryProgressData<HistoryQueryProgressOperationData>;
  processingMessage: string;
  processingPercentage: number;
}

const props = defineProps<Props>();

const { processingMessage, processingPercentage, progress } = toRefs(props);

const currentOperationData = computed(() => get(progress).currentOperationData);
</script>

<template>
  <RuiProgress
    v-if="processingMessage"
    circular
    :value="processingPercentage"
    size="30"
    show-label
    thickness="2"
    color="primary"
  />

  <div
    v-if="processingMessage"
    class="inline gap-2"
  >
    {{ processingMessage }}
    <template v-if="currentOperationData">
      <i18n-t
        v-if="currentOperationData.type === 'transaction'"
        keypath="dashboard.history_query_indicator.processing_operation_transaction"
        tag="span"
      >
        <template #status>
          {{ currentOperationData.status }}
        </template>
        <template #address>
          <span class="inline-flex items-center gap-1 align-middle ml-1.5 -mt-0.5">
            <ChainIcon
              v-if="currentOperationData.chain"
              :chain="currentOperationData.chain"
              size="1.25rem"
            />
            <HashLink
              v-if="currentOperationData.address"
              class="inline-flex align-middle"
              display-mode="text"
              :text="currentOperationData.address"
              :location="currentOperationData.chain"
            />
          </span>
        </template>
      </i18n-t>
      <i18n-t
        v-else-if="currentOperationData.type === 'event'"
        keypath="dashboard.history_query_indicator.processing_operation_event"
        tag="span"
      >
        <template #status>
          {{ currentOperationData.status }}
        </template>
        <template #name>
          <span class="inline-flex items-center gap-1 align-middle ml-1.5 -mt-0.5">
            <LocationIcon
              v-if="currentOperationData.location"
              :item="currentOperationData.location"
              horizontal
              size="1.25rem"
              class="-my-2"
            />
            {{ currentOperationData.name }}
          </span>
        </template>
        <template #location>
          {{ currentOperationData.location }}
        </template>
      </i18n-t>
    </template>
  </div>
</template>
