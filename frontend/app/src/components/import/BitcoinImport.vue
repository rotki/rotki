<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <ImportSource source="bitcoin_tax">
    <template #upload-title>
      <i18n-t
        scope="global"
        tag="span"
        keypath="import_data.bitcoin_tax.import"
      >
        <strong>{{ t('import_data.bitcoin_tax.import_types') }}</strong>
      </i18n-t>
    </template>
    <i18n-t
      scope="global"
      tag="span"
      keypath="import_data.note"
    >
      <strong>{{ t('import_data.bitcoin_tax.name') }}</strong>
    </i18n-t>
    <ul class="list-disc">
      <li>{{ t('import_data.bitcoin_tax.line_one') }}</li>
      <li>{{ t('import_data.bitcoin_tax.line_two') }}</li>
      <li>{{ t('import_data.bitcoin_tax.line_three') }}</li>
    </ul>
  </ImportSource>
</template>
