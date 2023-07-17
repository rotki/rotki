<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <div>
    <VRow>
      <VCol>
        <ImportSource source="rotki_events">
          <template #upload-title>
            <strong>
              {{ t('import_data.custom.import_events') }}
            </strong>
          </template>
        </ImportSource>
      </VCol>
      <VCol>
        <ImportSource source="rotki_trades">
          <template #upload-title>
            <strong>
              {{ t('import_data.custom.import_trades') }}
            </strong>
          </template>
        </ImportSource>
      </VCol>
    </VRow>
  </div>
</template>
