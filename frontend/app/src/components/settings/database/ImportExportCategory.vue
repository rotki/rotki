<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('database_settings.import_export.title') }}
    </template>
    <template #subtitle>
      {{ t('database_settings.import_export.subtitle') }}
    </template>
    <ManageCustomAssets />
  </SettingCategory>
</template>
