<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <ImportSource source="bitcoin_tax">
    <template #upload-title>
      <I18n tag="span" path="import_data.bitcoin_tax.import">
        <strong>{{ t('import_data.bitcoin_tax.import_types') }}</strong>
      </I18n>
    </template>
    <I18n tag="span" path="import_data.note">
      <strong>{{ t('import_data.bitcoin_tax.name') }}</strong>
    </I18n>
    <ul>
      <li>{{ t('import_data.bitcoin_tax.line_one') }}</li>
      <li>{{ t('import_data.bitcoin_tax.line_two') }}</li>
      <li>{{ t('import_data.bitcoin_tax.line_three') }}</li>
    </ul>
  </ImportSource>
</template>
