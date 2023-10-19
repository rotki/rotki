<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('data_management.title') }}
    </template>

    <div class="flex flex-col gap-4">
      <PurgeData />
      <PurgeImagesCache />
      <RefreshCache />
    </div>
  </SettingCategory>
</template>
