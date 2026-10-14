<script setup lang="ts">
import CopyButton from '@/modules/shell/components/CopyButton.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

defineProps<{
  identifier: string;
}>();

const emit = defineEmits<{
  edit: [];
  delete: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RowActions
    align="end"
    :edit-tooltip="t('asset_table.edit_tooltip')"
    :delete-tooltip="t('asset_table.delete_tooltip')"
    @edit-click="emit('edit')"
    @delete-click="emit('delete')"
  >
    <CopyButton
      :tooltip="t('asset_table.copy_identifier.tooltip')"
      :value="identifier"
    />
  </RowActions>
</template>
