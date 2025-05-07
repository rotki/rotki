<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <ImportSource source="bitmex_wallet_history">
    <template #upload-title>
      <i18n-t
        scope="global"
        tag="span"
        keypath="import_data.bitmex.import"
      >
        <strong>{{ t('import_data.bitmex.import_types') }}</strong>
      </i18n-t>
    </template>
    <i18n-t
      scope="global"
      tag="span"
      keypath="import_data.note"
    >
      <strong>{{ t('import_data.bitmex.name') }}</strong>
    </i18n-t>
    <ul class="list-disc">
      <li>{{ t('import_data.bitmex.line_one') }}</li>
      <li>{{ t('import_data.bitmex.line_two') }}</li>
    </ul>
  </ImportSource>
</template>
