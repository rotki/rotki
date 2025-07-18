<script setup lang="ts">
import { usePremium } from '@/composables/premium';
import { useSync } from '@/composables/session/sync';
import { useTaskStore } from '@/store/tasks';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, type SyncAction } from '@/types/session/sync';
import { TaskType } from '@/types/task-type';

defineProps<{ pending: boolean }>();

const emit = defineEmits<{
  (event: 'action', action: SyncAction): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const premium = usePremium();
const UPLOAD: SyncAction = SYNC_UPLOAD;
const DOWNLOAD: SyncAction = SYNC_DOWNLOAD;

function action(action: SyncAction) {
  emit('action', action);
}

const { uploadStatus } = useSync();

const { useIsTaskRunning } = useTaskStore();

const isTokenDetecting = useIsTaskRunning(TaskType.FETCH_DETECTED_TOKENS);
const isQueryingBlockchain = useIsTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
const isLoopringLoading = useIsTaskRunning(TaskType.L2_LOOPRING);
const isManualBalancesLoading = useIsTaskRunning(TaskType.MANUAL_BALANCES);
const isExchangeBalancesLoading = useIsTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES);

const loading = logicOr(
  isTokenDetecting,
  isQueryingBlockchain,
  isLoopringLoading,
  isManualBalancesLoading,
  isExchangeBalancesLoading,
);
</script>

<template>
  <div class="flex flex-row justify-between gap-1">
    <RuiTooltip
      :open-delay="400"
      class="w-full"
    >
      <template #activator>
        <RuiButton
          :variant="uploadStatus ? 'default' : 'outlined'"
          color="primary"
          class="w-full"
          :disabled="!premium || pending || loading"
          @click="action(UPLOAD)"
        >
          <template #prepend>
            <RuiIcon name="lu-cloud-upload-fill" />
          </template>
          {{ t('common.actions.push') }}
        </RuiButton>
      </template>
      <span>{{ t('sync_buttons.upload_tooltip') }}</span>
    </RuiTooltip>

    <RuiTooltip
      :open-delay="400"
      class="w-full"
    >
      <template #activator>
        <RuiButton
          variant="outlined"
          color="primary"
          class="w-full"
          :disabled="!premium || pending || !!uploadStatus || loading"
          @click="action(DOWNLOAD)"
        >
          <template #prepend>
            <RuiIcon name="lu-cloud-download-fill" />
          </template>
          {{ t('common.actions.pull') }}
        </RuiButton>
      </template>
      <span>{{ t('sync_buttons.download_tooltip') }}</span>
    </RuiTooltip>
  </div>
</template>
