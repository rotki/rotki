<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <ImportSource source="bisq_trades">
    <template #upload-title>
      <i18n-t
        scope="global"
        tag="span"
        keypath="import_data.bisq.import"
      >
        <strong>{{ t('import_data.bisq.import_trade') }}</strong>
      </i18n-t>
    </template>
    <i18n-t
      scope="global"
      tag="span"
      keypath="import_data.note"
    >
      <strong>{{ t('import_data.bisq.name') }}</strong>
    </i18n-t>
    <ul class="list-disc">
      <li>{{ t('import_data.bisq.line_one') }}</li>
    </ul>
  </ImportSource>
</template>
