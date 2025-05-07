<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="grid grid-cols-2 gap-4">
    <ImportSource source="rotki_events">
      <template #upload-title>
        <strong>
          {{ t('import_data.custom.import_events') }}
        </strong>
      </template>
    </ImportSource>
    <ImportSource source="rotki_trades">
      <template #upload-title>
        <strong>
          {{ t('import_data.custom.import_trades') }}
        </strong>
      </template>
    </ImportSource>
  </div>
</template>
