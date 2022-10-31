<template>
  <div>
    <v-row>
      <v-col>
        <import-source source="rotki_events">
          <template #upload-title>
            <strong>
              {{ t('import_data.custom.import_events') }}
            </strong>
          </template>
        </import-source>
      </v-col>
      <v-col>
        <import-source source="rotki_trades">
          <template #upload-title>
            <strong>
              {{ t('import_data.custom.import_trades') }}
            </strong>
          </template>
        </import-source>
      </v-col>
    </v-row>
  </div>
</template>
<script setup lang="ts">
import ImportSource from '@/components/import/ImportSource.vue';

const { t } = useI18n();
</script>
