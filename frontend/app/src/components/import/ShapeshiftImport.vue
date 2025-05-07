<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <ImportSource source="shapeshift_trades">
    <template #upload-title>
      <i18n-t
        scope="global"
        tag="span"
        keypath="import_data.shapeshift.import"
      >
        <strong>{{ t('import_data.shapeshift.import_trade') }}</strong>
      </i18n-t>
    </template>
    <i18n-t
      scope="global"
      tag="span"
      keypath="import_data.note"
    >
      <strong>{{ t('import_data.shapeshift.name') }}</strong>
    </i18n-t>
    <ul class="list-disc">
      <li>{{ t('import_data.shapeshift.line_one') }}</li>
      <li>{{ t('import_data.shapeshift.line_two') }}</li>
    </ul>
  </ImportSource>
</template>
