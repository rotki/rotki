<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <ImportSource source="bisq_trades">
    <template #upload-title>
      <I18n tag="span" path="import_data.bisq.import">
        <strong>{{ t('import_data.bisq.import_trade') }}</strong>
      </I18n>
    </template>
    <I18n tag="span" path="import_data.note">
      <strong>{{ t('import_data.bisq.name') }}</strong>
    </I18n>
    <ul>
      <li>{{ t('import_data.bisq.line_one') }}</li>
    </ul>
  </ImportSource>
</template>
