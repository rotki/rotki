<template>
  <import-source source="shapeshift_trades">
    <template #upload-title>
      <i18n tag="span" path="import_data.shapeshift.import">
        <strong>{{ t('import_data.shapeshift.import_trade') }}</strong>
      </i18n>
    </template>
    <i18n tag="span" path="import_data.shapeshift.note">
      <strong>{{ t('import_data.shapeshift.source_name') }}</strong>
    </i18n>
    <ul>
      <li>{{ t('import_data.shapeshift.line_one') }}</li>
      <li>{{ t('import_data.shapeshift.line_two') }}</li>
    </ul>
  </import-source>
</template>
<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n();
</script>
