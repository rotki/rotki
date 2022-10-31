<template>
  <import-source source="nexo">
    <template #upload-title>
      <i18n tag="span" path="import_data.nexo.import">
        <strong>{{ t('import_data.nexo.import_transactions') }}</strong>
      </i18n>
    </template>
    <i18n tag="span" path="import_data.nexo.note">
      <strong>{{ t('import_data.nexo.source_name') }}</strong>
    </i18n>
    <ul>
      <li>{{ t('import_data.nexo.line_one') }}</li>
    </ul>
  </import-source>
</template>
<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n();
</script>
