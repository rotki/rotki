<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('data_management.title') }}
    </template>

    <div>
      <PurgeData />
    </div>

    <div class="mt-4">
      <PurgeImagesCache />
    </div>

    <div class="mt-4">
      <RefreshCache />
    </div>
  </SettingCategory>
</template>
