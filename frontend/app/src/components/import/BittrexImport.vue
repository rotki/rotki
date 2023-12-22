<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <div>
    <ImportSource source="bittrex">
      <template #upload-title>
        <i18n tag="span" path="import_data.bittrex.import">
          <strong>{{ t('import_data.bittrex.import_types') }}</strong>
        </i18n>
      </template>
      <div class="text-rui-text-secondary">
        {{ t('import_data.bittrex.warning') }}
      </div>
    </ImportSource>
  </div>
</template>
