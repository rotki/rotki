<script setup lang="ts">
/**
 * The sync menu's way into the remote backup deletion.
 *
 * It is off while no backup is known, and says why. The menu asks the server when it opens and no
 * backup is known, so the button only ever deletes and never doubles as a check.
 */
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

const { checkFailed = false, checking = false, disabled = false, noBackup = false } = defineProps<{
  disabled?: boolean;
  /** No backup is known on the server, so there is nothing to delete. */
  noBackup?: boolean;
  /** The menu is asking the server whether it stores a backup. */
  checking?: boolean;
  /** Asking the server failed, so whether a backup exists is not known. */
  checkFailed?: boolean;
}>();

const emit = defineEmits<{
  open: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const reason = computed<string>(() => {
  if (checking)
    return t('delete_remote_backup.checking');
  if (!noBackup)
    return '';
  return checkFailed ? t('delete_remote_backup.check_failed') : t('delete_remote_backup.empty');
});
</script>

<template>
  <RuiTooltip
    :disabled="!reason"
    :open-delay="400"
    class="w-full"
    :text="reason"
  >
    <template #activator>
      <RuiButton
        variant="text"
        size="sm"
        class="w-full justify-start! text-rui-text-secondary"
        :disabled="disabled || noBackup || checking"
        :loading="checking"
        data-testid="sync-delete-remote-backup"
        @click="emit('open')"
      >
        <template #prepend>
          <RuiIcon
            name="lu-trash-2"
            size="14"
          />
        </template>
        {{ t('delete_remote_backup.entry') }}
      </RuiButton>
    </template>
  </RuiTooltip>
</template>
