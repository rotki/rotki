<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <ImportSource source="bitmex_wallet_history">
    <template #upload-title>
      <i18n tag="span" path="import_data.bitmex.import">
        <strong>{{ t('import_data.bitmex.import_types') }}</strong>
      </i18n>
    </template>
    <i18n tag="span" path="import_data.note">
      <strong>{{ t('import_data.bitmex.name') }}</strong>
    </i18n>
    <ul class="list-disc">
      <li>{{ t('import_data.bitmex.line_one') }}</li>
      <li>{{ t('import_data.bitmex.line_two') }}</li>
    </ul>
  </ImportSource>
</template>
