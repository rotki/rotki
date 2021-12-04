<template>
  <div>
    <v-row>
      <v-col>
        <import-source source="blockfi-trades">
          <template #upload-title>
            <i18n tag="span" path="import_data.blockfi.import">
              <strong> {{ $t('import_data.blockfi.import_trade') }}</strong>
            </i18n>
          </template>
        </import-source>
      </v-col>
      <v-col>
        <import-source source="blockfi-transactions">
          <template #upload-title>
            <i18n tag="span" path="import_data.blockfi.import">
              <strong>
                {{ $t('import_data.blockfi.import_transactions') }}
              </strong>
            </i18n>
          </template>
        </import-source>
      </v-col>
    </v-row>

    <i18n tag="span" path="import_data.blockfi.note">
      <strong>{{ $t('import_data.blockfi.source_name') }}</strong>
    </i18n>
    <ul>
      <li>{{ $t('import_data.blockfi.line_one') }}</li>
      <li>{{ $t('import_data.blockfi.line_two') }}</li>
    </ul>
  </div>
</template>
<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import ImportSource from '@/components/import/ImportSource.vue';

export default defineComponent({
  name: 'BlockFiImport',
  components: { ImportSource }
});
</script>
