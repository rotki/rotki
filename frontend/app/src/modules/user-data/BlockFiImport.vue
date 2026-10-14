<script setup lang="ts">
import ImportNotes from '@/modules/user-data/ImportNotes.vue';
import ImportSource from '@/modules/user-data/ImportSource.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="grid items-start gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
    <div class="flex flex-col gap-4">
      <ImportSource
        source="blockfi_trades"
        :notes="false"
      >
        <template #upload-title>
          <i18n-t
            scope="global"
            tag="div"
            keypath="import_data.blockfi.import"
          >
            <strong>{{ t('import_data.blockfi.import_trade') }}</strong>
          </i18n-t>
          <div class="mt-0.5 text-rui-text-secondary">
            {{ t('import_data.blockfi.trades_file') }}
          </div>
        </template>
      </ImportSource>
      <ImportSource
        source="blockfi_transactions"
        :notes="false"
      >
        <template #upload-title>
          <i18n-t
            scope="global"
            tag="div"
            keypath="import_data.blockfi.import"
          >
            <strong>{{ t('import_data.blockfi.import_transactions') }}</strong>
          </i18n-t>
          <div class="mt-0.5 text-rui-text-secondary">
            {{ t('import_data.blockfi.transactions_file') }}
          </div>
        </template>
      </ImportSource>
    </div>

    <ImportNotes>
      <ul>
        <li>{{ t('import_data.blockfi.line_one') }}</li>
      </ul>
    </ImportNotes>
  </div>
</template>
