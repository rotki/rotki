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
    class="flex flex-col gap-4"
  >
    <RuiCard>
      <div class="flex justify-between items-center gap-2">
        {{ t('asset_update.restore.soft_reset_hint') }}
        <RuiButton
          variant="outlined"
          color="error"
          :loading="loading"
          @click="showRestoreConfirmation('soft')"
        >
          {{ t('asset_update.restore.soft_reset') }}
        </RuiButton>
      </div>
    </RuiCard>
    <RuiCard>
      <div class="flex justify-between items-center gap-2">
        {{ t('asset_update.restore.hard_reset_hint') }}
        <RuiButton
          color="error"
          :loading="loading"
          @click="showRestoreConfirmation('hard')"
        >
          {{ t('asset_update.restore.hard_reset') }}
        </RuiButton>
      </div>
    </RuiCard>
  </div>
</template>
