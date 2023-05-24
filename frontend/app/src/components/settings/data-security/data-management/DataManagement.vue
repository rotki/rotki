<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <setting-category>
    <template #title>
      {{ t('data_management.title') }}
    </template>

    <div>
      <purge-data />
    </div>

    <div class="mt-4">
      <purge-images-cache />
    </div>

    <div class="mt-4">
      <refresh-cache />
    </div>
  </setting-category>
</template>
