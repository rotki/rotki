<script setup lang="ts">
/**
 * The sync menu's way into the remote backup deletion. It is off while the server is known to
 * store no backup, which the last upload line of the menu also shows as never.
 */
const { disabled = false, noBackup = false } = defineProps<{
  disabled?: boolean;
  /** The server stored no backup when last asked, so there is nothing to delete. */
  noBackup?: boolean;
}>();

const emit = defineEmits<{
  open: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    :disabled="!noBackup"
    :open-delay="400"
    class="w-full"
    :text="t('delete_remote_backup.empty')"
  >
    <template #activator>
      <RuiButton
        variant="text"
        size="sm"
        class="w-full justify-start! text-rui-text-secondary"
        :disabled="noBackup || disabled"
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
