<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('database_settings.user_backups.title') }}
    </template>
    <template #subtitle>
      {{ t('database_settings.user_backups.subtitle') }}
    </template>
    <BackupManager />
  </SettingCategory>
</template>
