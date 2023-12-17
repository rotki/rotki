<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <ImportSource source="bittrex">
    <template #upload-title>
      <i18n tag="span" path="import_data.bittrex.import">
        <strong>{{ t('import_data.bittrex.import_types') }}</strong>
      </i18n>
    </template>
  </ImportSource>
</template>
