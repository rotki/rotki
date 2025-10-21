<script setup lang="ts">
import type { BalanceQueryProgressType, CommonQueryProgressData } from '@/modules/dashboard/progress/types';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import HashLink from '@/modules/common/links/HashLink.vue';
import { TaskType } from '@/types/task-type';

interface BalanceQueryProgressOperationData {
  type: BalanceQueryProgressType;
  chain?: string;
  address?: string;
  status: string;
}

interface Props {
  progress: CommonQueryProgressData<BalanceQueryProgressOperationData>;
  processingMessage: string;
  processingPercentage: number;
}

const props = defineProps<Props>();

const { processingMessage, processingPercentage, progress } = toRefs(props);

const currentOperationData = computed(() => get(progress).currentOperationData);
</script>

<template>
  <RuiProgress
    circular
    :value="processingPercentage"
    size="30"
    show-label
    thickness="2"
    color="primary"
  />

  <div class="inline gap-2">
    {{ processingMessage }}
    <template v-if="currentOperationData && currentOperationData.type === TaskType.FETCH_DETECTED_TOKENS">
      <span class="inline-flex items-center gap-1">
        <span>&nbsp;</span>
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
  </div>
</template>
