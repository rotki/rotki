<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <ImportSource source="bitstamp">
    <template #upload-title>
      <i18n tag="span" path="import_data.bitstamp.import">
        <strong>{{ t('import_data.bitstamp.import_types') }}</strong>
      </i18n>
    </template>
  </ImportSource>
</template>
