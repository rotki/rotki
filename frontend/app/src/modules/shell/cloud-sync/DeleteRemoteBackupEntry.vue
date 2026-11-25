<script setup lang="ts">
/**
 * The sync menu's way into the remote backup deletion.
 *
 * It stays enabled whether or not the menu's last upload line shows a backup: that time is only
 * refreshed at login and on uploads, so it can be stale. The panel asks the server and says when
 * there is nothing to delete.
 */
const { disabled = false } = defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{
  open: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiButton
    variant="text"
    size="sm"
    class="w-full justify-start! text-rui-text-secondary"
    :disabled="disabled"
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
