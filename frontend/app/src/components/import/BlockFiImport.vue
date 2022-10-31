<template>
  <div>
    <v-row>
      <v-col>
        <import-source source="blockfi_trades">
          <template #upload-title>
            <i18n tag="span" path="import_data.blockfi.import">
              <strong> {{ t('import_data.blockfi.import_trade') }}</strong>
            </i18n>
          </template>
        </import-source>
      </v-col>
      <v-col>
        <import-source source="blockfi_transactions">
          <template #upload-title>
            <i18n tag="span" path="import_data.blockfi.import">
              <strong>
                {{ t('import_data.blockfi.import_transactions') }}
              </strong>
            </i18n>
          </template>
        </import-source>
      </v-col>
    </v-row>

    <div class="pt-4">
      <i18n tag="span" path="import_data.blockfi.note">
        <strong>{{ t('import_data.blockfi.source_name') }}</strong>
      </i18n>
      <ul>
        <li>{{ t('import_data.blockfi.line_one') }}</li>
        <li>{{ t('import_data.blockfi.line_two') }}</li>
      </ul>
    </div>
  </div>
</template>
<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n();
</script>
