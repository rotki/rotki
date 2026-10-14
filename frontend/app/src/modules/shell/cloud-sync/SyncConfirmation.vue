<script setup lang="ts">
import AskUserUponSizeDiscrepancySetting from '@/modules/settings/general/AskUserUponSizeDiscrepancySetting.vue';

/**
 * Confirms a force sync in place, inside the sync menu. Either direction overwrites one side
 * wholesale, so the action stays disabled until the user acknowledges it.
 */
const checked = defineModel<boolean>('checked', { required: true });

const { download, syncing = false, sizeDiscrepancy = false } = defineProps<{
  /** Pulling replaces the local database and logs out; pushing replaces the server backup. */
  download: boolean;
  syncing?: boolean;
  /** The last upload stopped on a size discrepancy, so the setting that governs it is offered. */
  sizeDiscrepancy?: boolean;
}>();

const emit = defineEmits<{
  cancel: [];
  confirm: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const choice = computed<number>(() => (download ? 2 : 1));
</script>

<template>
  <div
    class="flex flex-col gap-3 rounded-rui-control border border-rui-error/40 bg-rui-error/5 p-3"
    data-testid="sync-confirmation"
  >
    <div class="flex gap-2">
      <RuiIcon
        name="lu-triangle-alert"
        size="18"
        class="text-rui-error shrink-0 mt-0.5"
      />
      <div class="flex flex-col gap-1">
        <div class="text-sm font-medium text-rui-text">
          {{ t('sync_indicator.upload_confirmation.title', choice) }}
        </div>
        <div class="text-sm text-rui-text-secondary">
          {{ download ? t('sync_indicator.upload_confirmation.message_download') : t('sync_indicator.upload_confirmation.message_upload') }}
          <template v-if="download">
            {{ t('sync_indicator.upload_confirmation.message_download_relogin') }}
          </template>
        </div>
      </div>
    </div>
    <AskUserUponSizeDiscrepancySetting
      v-if="sizeDiscrepancy"
      dialog
      confirm
    />
    <RuiCheckbox
      v-model="checked"
      color="primary"
      size="sm"
      hide-details
      data-testid="sync-confirm-check"
    >
      {{ t('sync_indicator.upload_confirmation.confirm_check') }}
    </RuiCheckbox>
    <div class="flex justify-end gap-2">
      <RuiButton
        variant="text"
        size="sm"
        :disabled="syncing"
        data-testid="sync-confirm-cancel"
        @click="emit('cancel')"
      >
        {{ t('common.actions.cancel') }}
      </RuiButton>
      <RuiButton
        color="error"
        size="sm"
        :disabled="!checked"
        :loading="syncing"
        data-testid="sync-confirm-action"
        @click="emit('confirm')"
      >
        {{ t('sync_indicator.upload_confirmation.action', choice) }}
      </RuiButton>
    </div>
  </div>
</template>
