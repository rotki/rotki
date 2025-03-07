<script setup lang="ts">
import HistoryEventsSkippedExternalEvents from '@/components/history/events/HistoryEventsSkippedExternalEvents.vue';
import SettingsPage from '@/components/settings/controls/SettingsPage.vue';
import BackupManager from '@/components/settings/data-security/backups/BackupManager.vue';
import DataManagement from '@/components/settings/data-security/data-management/DataManagement.vue';
import AssetDatabaseCategory from '@/components/settings/database/AssetDatabaseCategory.vue';
import DatabaseInformationCategory from '@/components/settings/database/DatabaseInformationCategory.vue';
import ImportExportCategory from '@/components/settings/database/ImportExportCategory.vue';
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_DATABASE,
  },
});

const { t } = useI18n();

enum Category {
  DATABASE_INFO = 'database-info',
  USER_BACKUPS = 'user-backups',
  MANAGE_DATA = 'manage-data',
  SKIPPED_EVENTS = 'skipped-events',
  IMPORT_EXPORT = 'import-export',
  ASSET_DATABASE = 'asset-database',
}

const navigation = [
  { id: Category.DATABASE_INFO, label: t('database_settings.database_info.title') },
  { id: Category.USER_BACKUPS, label: t('database_settings.user_backups.title') },
  { id: Category.MANAGE_DATA, label: t('database_settings.manage_data.title') },
  { id: Category.SKIPPED_EVENTS, label: t('database_settings.skipped_events.title') },
  { id: Category.IMPORT_EXPORT, label: t('database_settings.import_export.title') },
  { id: Category.ASSET_DATABASE, label: t('database_settings.asset_database.title') },
];
</script>

<template>
  <SettingsPage
    class="database-settings"
    :navigation="navigation"
  >
    <DatabaseInformationCategory :id="Category.DATABASE_INFO" />
    <BackupManager :id="Category.USER_BACKUPS" />
    <DataManagement :id="Category.MANAGE_DATA" />
    <HistoryEventsSkippedExternalEvents :id="Category.SKIPPED_EVENTS" />
    <ImportExportCategory :id="Category.IMPORT_EXPORT" />
    <AssetDatabaseCategory :id="Category.ASSET_DATABASE" />
  </SettingsPage>
</template>

<style scoped lang="scss">
.database-settings {
  &_database-info {
    font-size: 2em;
  }
}
</style>
