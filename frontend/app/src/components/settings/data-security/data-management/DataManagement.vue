<script setup lang="ts">
const { tc } = useI18n();
</script>

<template>
  <setting-category>
    <template #title>
      {{ tc('data_management.title') }}
    </template>

    <div>
      <purge-data />
    </div>

    <div class="mt-4">
      <purge-images-cache />
    </div>
  </setting-category>
</template>
