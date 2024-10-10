<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory class="pt-5 border-t border-default">
    <template #title>
      {{ t('database_settings.import_export.title') }}
    </template>
    <template #subtitle>
      {{ t('database_settings.import_export.subtitle') }}
    </template>
    <ManageCustomAssets />
  </SettingCategory>
</template>
