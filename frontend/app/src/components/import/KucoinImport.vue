<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n();
</script>

<template>
  <ImportSource source="kucoin">
    <template #upload-title>
      <i18n-t
        tag="span"
        keypath="import_data.kucoin.import"
      >
        <strong>{{ t('import_data.kucoin.import_types') }}</strong>
      </i18n-t>
    </template>
    <i18n-t
      tag="span"
      keypath="import_data.note"
    >
      <strong>{{ t('import_data.kucoin.name') }}</strong>
    </i18n-t>
    <ul class="list-disc">
      <li>{{ t('import_data.kucoin.line_one') }}</li>
    </ul>
  </ImportSource>
</template>
