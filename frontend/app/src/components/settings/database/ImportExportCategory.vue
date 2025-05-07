<script setup lang="ts">
import ManageCustomAssets from '@/components/settings/data-security/ManageCustomAssets.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';

const { t } = useI18n({ useScope: 'global' });
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
