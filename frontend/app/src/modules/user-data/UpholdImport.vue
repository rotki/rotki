<script setup lang="ts">
import ImportSource from '@/modules/user-data/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <ImportSource source="uphold_transactions">
    <template #upload-title>
      <i18n-t
        scope="global"
        tag="span"
        keypath="import_data.uphold.import"
      >
        <strong>{{ t('import_data.uphold.import_trade') }}</strong>
      </i18n-t>
    </template>
    <ul>
      <li>{{ t('import_data.uphold.line_one') }}</li>
      <li>{{ t('import_data.uphold.line_two') }}</li>
    </ul>
  </ImportSource>
</template>
