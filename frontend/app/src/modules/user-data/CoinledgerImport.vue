<script setup lang="ts">
import ImportSource from '@/modules/user-data/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <ImportSource source="coinledger">
    <ul>
      <li>{{ t('import_data.coinledger.line_one') }}</li>
    </ul>
  </ImportSource>
</template>
