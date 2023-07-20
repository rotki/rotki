<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <div>
    <VRow>
      <VCol>
        <ImportSource source="blockfi_trades">
          <template #upload-title>
            <i18n tag="span" path="import_data.blockfi.import">
              <strong> {{ t('import_data.blockfi.import_trade') }}</strong>
            </i18n>
          </template>
        </ImportSource>
      </VCol>
      <VCol>
        <ImportSource source="blockfi_transactions">
          <template #upload-title>
            <i18n tag="span" path="import_data.blockfi.import">
              <strong>
                {{ t('import_data.blockfi.import_transactions') }}
              </strong>
            </i18n>
          </template>
        </ImportSource>
      </VCol>
    </VRow>

    <div class="pt-4">
      <i18n tag="span" path="import_data.note">
        <strong>{{ t('import_data.blockfi.name') }}</strong>
      </i18n>
      <ul>
        <li>{{ t('import_data.blockfi.line_one') }}</li>
        <li>{{ t('import_data.blockfi.line_two') }}</li>
      </ul>
    </div>
  </div>
</template>
