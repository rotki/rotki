<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <ImportSource source="binance">
    <i18n-t
      tag="span"
      keypath="import_data.note"
    >
      <strong>{{ t('import_data.binance.name') }}</strong>
    </i18n-t>
    <ul class="list-disc">
      <li>{{ t('import_data.binance.line_one') }}</li>
      <li>{{ t('import_data.binance.line_two') }}</li>
    </ul>
  </ImportSource>
</template>
