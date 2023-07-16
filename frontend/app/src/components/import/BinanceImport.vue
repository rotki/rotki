<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <ImportSource source="binance">
    <I18n tag="span" path="import_data.note">
      <strong>{{ t('import_data.binance.name') }}</strong>
    </I18n>
    <ul>
      <li>{{ t('import_data.binance.line_one') }}</li>
      <li>{{ t('import_data.binance.line_two') }}</li>
    </ul>
  </ImportSource>
</template>
