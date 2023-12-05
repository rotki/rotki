<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <ImportSource source="bitcoin_tax">
    <template #upload-title>
      <i18n tag="span" path="import_data.bitcoin_tax.import">
        <strong>{{ t('import_data.bitcoin_tax.import_types') }}</strong>
      </i18n>
    </template>
    <i18n tag="span" path="import_data.note">
      <strong>{{ t('import_data.bitcoin_tax.name') }}</strong>
    </i18n>
    <ul class="list-disc">
      <li>{{ t('import_data.bitcoin_tax.line_one') }}</li>
      <li>{{ t('import_data.bitcoin_tax.line_two') }}</li>
      <li>{{ t('import_data.bitcoin_tax.line_three') }}</li>
    </ul>
  </ImportSource>
</template>
