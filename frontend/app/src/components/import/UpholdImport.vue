<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <ImportSource source="uphold_transactions">
    <template #upload-title>
      <I18n tag="span" path="import_data.uphold.import">
        <strong>{{ t('import_data.uphold.import_trade') }}</strong>
      </I18n>
    </template>
    <I18n tag="span" path="import_data.note">
      <strong>{{ t('import_data.uphold.name') }}</strong>
    </I18n>
    <ul>
      <li>{{ t('import_data.uphold.line_one') }}</li>
      <li>{{ t('import_data.uphold.line_two') }}</li>
    </ul>
  </ImportSource>
</template>
