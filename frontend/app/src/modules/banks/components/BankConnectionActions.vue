<script setup lang="ts">
import RowActions from '@/modules/shell/components/RowActions.vue';

const { authenticationRequired = false, syncing = false } = defineProps<{
  authenticationRequired?: boolean;
  syncing?: boolean;
}>();

const emit = defineEmits<{
  authenticate: [];
  sync: [];
  edit: [];
  delete: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center justify-center gap-1">
    <RuiTooltip
      v-if="authenticationRequired"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          variant="text"
          icon
          color="warning"
          data-testid="bank-authenticate"
          @click="emit('authenticate')"
        >
          <RuiIcon name="lu-shield-check" />
        </RuiButton>
      </template>
      {{ t('bank_settings.sync.failed') }}
    </RuiTooltip>
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
