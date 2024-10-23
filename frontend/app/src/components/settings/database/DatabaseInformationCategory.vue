<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('database_settings.database_info.title') }}
    </template>
    <template #subtitle>
      {{ t('database_settings.database_info.subtitle') }}
    </template>
    <DatabaseInformation />
  </SettingCategory>
</template>
