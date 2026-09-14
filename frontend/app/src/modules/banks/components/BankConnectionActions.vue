<script setup lang="ts">
import RowActions from '@/modules/shell/components/RowActions.vue';

const { syncing = false } = defineProps<{
  syncing?: boolean;
}>();

const emit = defineEmits<{
  sync: [];
  edit: [];
  delete: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center justify-center gap-1">
    <RuiTooltip :open-delay="400">
      <template #activator>
        <RuiButton
          variant="text"
          icon
          :loading="syncing"
          data-testid="bank-sync"
          @click="emit('sync')"
        >
          <RuiIcon name="lu-refresh-cw" />
        </RuiButton>
      </template>
      {{ t('bank_settings.sync.tooltip') }}
    </RuiTooltip>
    <RowActions
      align="center"
      :delete-tooltip="t('bank_settings.delete.tooltip')"
      :edit-tooltip="t('bank_settings.edit.tooltip')"
      @delete-click="emit('delete')"
      @edit-click="emit('edit')"
    />
  </div>
</template>
