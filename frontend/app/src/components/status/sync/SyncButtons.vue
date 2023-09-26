<script setup lang="ts">
import {
  SYNC_DOWNLOAD,
  SYNC_UPLOAD,
  type SyncAction
} from '@/types/session/sync';

defineProps<{ pending: boolean }>();

const emit = defineEmits<{
  (event: 'action', action: SyncAction): void;
}>();

const { t } = useI18n();

const { premium } = storeToRefs(usePremiumStore());
const UPLOAD: SyncAction = SYNC_UPLOAD;
const DOWNLOAD: SyncAction = SYNC_DOWNLOAD;

const action = (action: SyncAction) => {
  emit('action', action);
};
</script>

<template>
  <div class="flex flex-row justify-between gap-1">
    <RuiTooltip open-delay="400" class="w-full">
      <template #activator>
        <RuiButton
          variant="outlined"
          color="primary"
          class="w-full"
          :disabled="!premium || pending"
          @click="action(UPLOAD)"
        >
          <template #prepend>
            <RuiIcon name="upload-cloud-line" />
          </template>
          {{ t('common.actions.push') }}
        </RuiButton>
      </template>
      <span>{{ t('sync_buttons.upload_tooltip') }}</span>
    </RuiTooltip>

    <RuiTooltip open-delay="400" class="w-full">
      <template #activator>
        <RuiButton
          variant="outlined"
          color="primary"
          class="w-full"
          :disabled="!premium || pending"
          @click="action(DOWNLOAD)"
        >
          <template #prepend>
            <RuiIcon name="download-cloud-line" />
          </template>
          {{ t('common.actions.pull') }}
        </RuiButton>
      </template>
      <span>{{ t('sync_buttons.download_tooltip') }}</span>
    </RuiTooltip>
  </div>
</template>
