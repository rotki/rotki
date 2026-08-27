<script setup lang="ts">
import DatabaseBackups from '@/modules/settings/data-security/backups/DatabaseBackups.vue';
import { useDatabaseBackups } from '@/modules/settings/data-security/backups/use-database-backups';
import SettingCategoryHeader from '@/modules/settings/SettingCategoryHeader.vue';

const { t } = useI18n({ useScope: 'global' });

const {
  backup,
  backups,
  directory,
  loadInfo,
  loading,
  modelSelected,
  remove,
  saving,
  showMassDeleteConfirmation,
} = useDatabaseBackups();
</script>

<template>
  <div>
    <div class="pb-5 flex flex-wrap gap-4 items-center justify-between">
      <SettingCategoryHeader>
        <template #title>
          {{ t('database_settings.user_backups.title') }}
        </template>
        <template #subtitle>
          {{ t('database_settings.user_backups.subtitle') }}
        </template>
      </SettingCategoryHeader>
      <div class="flex flex-wrap gap-2">
        <RuiButton
          v-if="modelSelected.length > 0"
          color="error"
          @click="showMassDeleteConfirmation()"
        >
          {{ t('database_settings.user_backups.delete_selected') }}
        </RuiButton>
        <RuiButton
          variant="outlined"
          color="primary"
          :loading="loading"
          @click="loadInfo()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-refresh-ccw"
              size="16"
            />
          </template>
          {{ t('common.refresh') }}
        </RuiButton>
        <RuiButton
          color="primary"
          :disabled="saving"
          :loading="saving"
          @click="backup()"
        >
          {{ t('database_settings.user_backups.backup_button') }}
        </RuiButton>
      </div>
    </div>
    <DatabaseBackups
      v-model:selected="modelSelected"
      :loading="loading"
      :items="backups"
      :directory="directory"
      @remove="remove($event)"
    />
  </div>
</template>
