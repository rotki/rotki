<script setup lang="ts">
import SettingsPage from '@/components/settings/controls/SettingsPage.vue';
import BackupManager from '@/components/settings/data-security/backups/BackupManager.vue';
import DataManagement from '@/components/settings/data-security/data-management/DataManagement.vue';
import AssetDatabaseCategory from '@/components/settings/database/AssetDatabaseCategory.vue';
import DatabaseInformationCategory from '@/components/settings/database/DatabaseInformationCategory.vue';
import ImportExportCategory from '@/components/settings/database/ImportExportCategory.vue';
import { SettingsCategoryIds } from '@/composables/settings/types';
import { NoteLocation } from '@/modules/common/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_DATABASE,
  },
});

const { t } = useI18n({ useScope: 'global' });

const navigation = computed<{ id: string; label: string }[]>(() => [
  { id: SettingsCategoryIds.DATABASE_INFO, label: t('database_settings.database_info.title') },
  { id: SettingsCategoryIds.USER_BACKUPS, label: t('database_settings.user_backups.title') },
  { id: SettingsCategoryIds.MANAGE_DATA, label: t('database_settings.manage_data.title') },
  { id: SettingsCategoryIds.IMPORT_EXPORT, label: t('database_settings.import_export.title') },
  { id: SettingsCategoryIds.ASSET_DATABASE, label: t('database_settings.asset_database.title') },
]);
</script>

<template>
  <SettingsPage
    class="database-settings"
    :navigation="navigation"
  >
    <DatabaseInformationCategory :id="SettingsCategoryIds.DATABASE_INFO" />
    <BackupManager :id="SettingsCategoryIds.USER_BACKUPS" />
    <DataManagement :id="SettingsCategoryIds.MANAGE_DATA" />
    <ImportExportCategory :id="SettingsCategoryIds.IMPORT_EXPORT" />
    <AssetDatabaseCategory :id="SettingsCategoryIds.ASSET_DATABASE" />
  </SettingsPage>
</template>
