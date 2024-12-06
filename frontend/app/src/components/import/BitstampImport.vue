<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n();
</script>

<template>
  <ImportSource source="bitstamp">
    <template #upload-title>
      <i18n-t
        tag="span"
        keypath="import_data.bitstamp.import"
      >
        <strong>{{ t('import_data.bitstamp.import_types') }}</strong>
      </i18n-t>
    </template>
  </ImportSource>
</template>
