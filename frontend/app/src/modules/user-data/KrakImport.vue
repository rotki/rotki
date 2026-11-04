<script setup lang="ts">
import ImportSource from '@/modules/user-data/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <ImportSource source="krak">
    <ul>
      <li>{{ t('import_data.krak.line_one') }}</li>
      <li>{{ t('import_data.krak.line_two') }}</li>
    </ul>
  </ImportSource>
</template>
