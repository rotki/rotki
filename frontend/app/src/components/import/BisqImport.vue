<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <ImportSource source="bisq_trades">
    <template #upload-title>
      <i18n tag="span" path="import_data.bisq.import">
        <strong>{{ t('import_data.bisq.import_trade') }}</strong>
      </i18n>
    </template>
    <i18n tag="span" path="import_data.note">
      <strong>{{ t('import_data.bisq.name') }}</strong>
    </i18n>
    <ul class="list-disc">
      <li>{{ t('import_data.bisq.line_one') }}</li>
    </ul>
  </ImportSource>
</template>
