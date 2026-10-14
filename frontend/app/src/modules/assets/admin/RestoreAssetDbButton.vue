<script setup lang="ts">
import { useRestoreAssetDb } from '@/modules/assets/admin/use-restore-asset-db';
import ListItem from '@/modules/shell/components/ListItem.vue';

const { dropdown = false } = defineProps<{
  dropdown?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { loading, showRestoreConfirmation } = useRestoreAssetDb();
</script>

<template>
  <RuiMenu
    v-if="dropdown"
    :options="{ placement: 'left-start' }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="list"
        :disabled="loading"
        v-bind="{ ...attrs, id: 'reset-asset-activator' }"
      >
        <template #prepend>
          <RuiIcon name="lu-rotate-ccw" />
        </template>
        {{ t('asset_update.restore.title') }}
        <template #append>
          <RuiIcon name="lu-chevron-down" />
        </template>
      </RuiButton>
    </template>
    <ListItem
      :title="t('asset_update.restore.soft_reset')"
      :subtitle="t('asset_update.restore.soft_reset_hint')"
      @click="showRestoreConfirmation('soft')"
    />
    <ListItem
      :title="t('asset_update.restore.hard_reset')"
      :subtitle="t('asset_update.restore.hard_reset_hint')"
      @click="showRestoreConfirmation('hard')"
    />
  </RuiMenu>
  <div
    v-else
    class="flex flex-col rounded-rui-card border border-rui-divider between:border-t between:border-rui-divider"
  >
    <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 p-4">
      <div class="flex flex-col gap-0.5">
        <span class="text-sm font-medium text-rui-text">{{ t('asset_update.restore.soft_reset') }}</span>
        <span class="text-sm text-rui-text-secondary">{{ t('asset_update.restore.soft_reset_hint') }}</span>
      </div>
      <RuiButton
        variant="outlined"
        color="error"
        :loading="loading"
        data-testid="asset-db-soft-reset"
        @click="showRestoreConfirmation('soft')"
      >
        {{ t('asset_update.restore.soft_reset') }}
      </RuiButton>
    </div>
    <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 p-4">
      <div class="flex flex-col gap-0.5">
        <span class="text-sm font-medium text-rui-text">{{ t('asset_update.restore.hard_reset') }}</span>
        <span class="text-sm text-rui-text-secondary">{{ t('asset_update.restore.hard_reset_hint') }}</span>
      </div>
      <RuiButton
        color="error"
        :loading="loading"
        data-testid="asset-db-hard-reset"
        @click="showRestoreConfirmation('hard')"
      >
        {{ t('asset_update.restore.hard_reset') }}
      </RuiButton>
    </div>
  </div>
</template>
