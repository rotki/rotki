<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div>
    <div class="grid grid-cols-2 gap-4">
      <ImportSource source="blockfi_trades">
        <template #upload-title>
          <i18n-t
            scope="global"
            tag="span"
            keypath="import_data.blockfi.import"
          >
            <strong> {{ t('import_data.blockfi.import_trade') }}</strong>
          </i18n-t>
        </template>
      </ImportSource>
      <ImportSource source="blockfi_transactions">
        <template #upload-title>
          <i18n-t
            scope="global"
            tag="span"
            keypath="import_data.blockfi.import"
          >
            <strong>
              {{ t('import_data.blockfi.import_transactions') }}
            </strong>
          </i18n-t>
        </template>
      </ImportSource>
    </div>

    <div class="mt-4 text-sm leading-7 text-rui-text-secondary">
      <i18n-t
        scope="global"
        tag="span"
        keypath="import_data.note"
      >
        <strong>{{ t('import_data.blockfi.name') }}</strong>
      </i18n-t>
      <ul class="list-disc">
        <li>{{ t('import_data.blockfi.line_one') }}</li>
        <li>{{ t('import_data.blockfi.line_two') }}</li>
      </ul>
    </div>
  </div>
</template>
