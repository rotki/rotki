<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <div>
    <VRow>
      <VCol>
        <ImportSource source="blockfi_trades">
          <template #upload-title>
            <I18n tag="span" path="import_data.blockfi.import">
              <strong> {{ t('import_data.blockfi.import_trade') }}</strong>
            </I18n>
          </template>
        </ImportSource>
      </VCol>
      <VCol>
        <ImportSource source="blockfi_transactions">
          <template #upload-title>
            <I18n tag="span" path="import_data.blockfi.import">
              <strong>
                {{ t('import_data.blockfi.import_transactions') }}
              </strong>
            </I18n>
          </template>
        </ImportSource>
      </VCol>
    </VRow>

    <div class="pt-4">
      <I18n tag="span" path="import_data.note">
        <strong>{{ t('import_data.blockfi.name') }}</strong>
      </I18n>
      <ul>
        <li>{{ t('import_data.blockfi.line_one') }}</li>
        <li>{{ t('import_data.blockfi.line_two') }}</li>
      </ul>
    </div>
  </div>
</template>
