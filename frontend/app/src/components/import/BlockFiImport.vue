<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <div>
    <div class="grid grid-cols-2 gap-4">
      <ImportSource source="blockfi_trades">
        <template #upload-title>
          <i18n tag="span" path="import_data.blockfi.import">
            <strong> {{ t('import_data.blockfi.import_trade') }}</strong>
          </i18n>
        </template>
      </ImportSource>
      <ImportSource source="blockfi_transactions">
        <template #upload-title>
          <i18n tag="span" path="import_data.blockfi.import">
            <strong>
              {{ t('import_data.blockfi.import_transactions') }}
            </strong>
          </i18n>
        </template>
      </ImportSource>
    </div>

    <div class="pt-4">
      <i18n tag="span" path="import_data.note">
        <strong>{{ t('import_data.blockfi.name') }}</strong>
      </i18n>
      <ul class="list-disc">
        <li>{{ t('import_data.blockfi.line_one') }}</li>
        <li>{{ t('import_data.blockfi.line_two') }}</li>
      </ul>
    </div>
  </div>
</template>
