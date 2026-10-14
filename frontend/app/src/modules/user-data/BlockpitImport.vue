<script setup lang="ts">
import ImportSource from '@/modules/user-data/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <ImportSource source="blockpit">
    <ul>
      <li>{{ t('import_data.blockpit.line_one') }}</li>
    </ul>
  </ImportSource>
</template>
