<template>
  <import-source source="binance">
    <i18n tag="span" path="import_data.binance.note">
      <strong>{{ t('import_data.binance.source_name') }}</strong>
    </i18n>
    <ul>
      <li>{{ t('import_data.binance.line_one') }}</li>
      <li>{{ t('import_data.binance.line_two') }}</li>
    </ul>
  </import-source>
</template>
<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n();
</script>
