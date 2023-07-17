<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <ImportSource source="shapeshift_trades">
    <template #upload-title>
      <I18n tag="span" path="import_data.shapeshift.import">
        <strong>{{ t('import_data.shapeshift.import_trade') }}</strong>
      </I18n>
    </template>
    <I18n tag="span" path="import_data.note">
      <strong>{{ t('import_data.shapeshift.name') }}</strong>
    </I18n>
    <ul>
      <li>{{ t('import_data.shapeshift.line_one') }}</li>
      <li>{{ t('import_data.shapeshift.line_two') }}</li>
    </ul>
  </ImportSource>
</template>
