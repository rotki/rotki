<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <ImportSource source="nexo">
    <template #upload-title>
      <I18n tag="span" path="import_data.nexo.import">
        <strong>{{ t('import_data.nexo.import_transactions') }}</strong>
      </I18n>
    </template>
    <I18n tag="span" path="import_data.note">
      <strong>{{ t('import_data.nexo.name') }}</strong>
    </I18n>
    <ul>
      <li>{{ t('import_data.nexo.line_one') }}</li>
    </ul>
  </ImportSource>
</template>
