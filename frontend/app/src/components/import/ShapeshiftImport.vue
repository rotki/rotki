<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <ImportSource source="shapeshift_trades">
    <template #upload-title>
      <i18n tag="span" path="import_data.shapeshift.import">
        <strong>{{ t('import_data.shapeshift.import_trade') }}</strong>
      </i18n>
    </template>
    <i18n tag="span" path="import_data.note">
      <strong>{{ t('import_data.shapeshift.name') }}</strong>
    </i18n>
    <ul>
      <li>{{ t('import_data.shapeshift.line_one') }}</li>
      <li>{{ t('import_data.shapeshift.line_two') }}</li>
    </ul>
  </ImportSource>
</template>
