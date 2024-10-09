<script setup lang="ts">
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.SETTINGS_DATABASE,
  },
});

const { t } = useI18n();

enum Category {
  DATABASE_INFO = 'database-info',
  MANAGE_DATA = 'manage-data',
  USER_BACKUPS = 'user-backups',
  SKIPPED_EVENTS = 'skipped-events',
  IMPORT_EXPORT = 'import-export',
  ASSET_DATABASE = 'asset-database',
}

const navigation = [
  { id: Category.DATABASE_INFO, label: t('database_settings.database_info.title') },
  { id: Category.MANAGE_DATA, label: t('database_settings.manage_data.title') },
  { id: Category.USER_BACKUPS, label: t('database_settings.user_backups.title') },
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
    <DataManagement :id="Category.MANAGE_DATA" />
    <UserBackupsCategory :id="Category.USER_BACKUPS" />
    <SkippedEventsCategory :id="Category.SKIPPED_EVENTS" />
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
