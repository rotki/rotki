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
  <div class="d-flex flex-wrap mx-n1">
    <VTooltip top open-delay="400">
      <template #activator="{ on, attrs }">
        <VBtn
          v-bind="attrs"
          outlined
          depressed
          class="ma-1"
          color="primary"
          :disabled="!premium || pending"
          v-on="on"
          @click="action(UPLOAD)"
        >
          <VIcon>mdi-cloud-upload</VIcon>
          <span class="ml-2">{{ t('common.actions.push') }}</span>
        </VBtn>
      </template>
      <span>{{ t('sync_buttons.upload_tooltip') }}</span>
    </VTooltip>

    <VTooltip top open-delay="400">
      <template #activator="{ on, attrs }">
        <VBtn
          v-bind="attrs"
          outlined
          depressed
          class="ma-1"
          color="primary"
          :disabled="!premium || pending"
          v-on="on"
          @click="action(DOWNLOAD)"
        >
          <VIcon>mdi-cloud-download</VIcon>
          <span class="ml-2">{{ t('common.actions.pull') }}</span>
        </VBtn>
      </template>
      <span>{{ t('sync_buttons.download_tooltip') }}</span>
    </VTooltip>
  </div>
</template>
