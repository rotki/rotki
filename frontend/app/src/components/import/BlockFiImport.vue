<template>
  <import-source
    :source="['blockfi-trades', 'blockfi-transactions']"
    :icon="require('@/assets/images/import/blockfi.svg')"
  >
    <template #upload-title-0>
      <i18n tag="span" path="import_data.blockfi.import">
        <strong> {{ $t('import_data.blockfi.import_trade') }}</strong>
      </i18n>
    </template>
    <template #upload-title-1>
      <i18n tag="span" path="import_data.blockfi.import">
        <strong> {{ $t('import_data.blockfi.import_transactions') }}</strong>
      </i18n>
    </template>
    <i18n tag="span" path="import_data.blockfi.note">
      <strong>{{ $t('import_data.blockfi.name') }}</strong>
    </i18n>
    <ul>
      <li>{{ $t('import_data.blockfi.line_one') }}</li>
      <li>{{ $t('import_data.blockfi.line_two') }}</li>
    </ul>
  </import-source>
</template>
<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import ImportSource from '@/components/import/ImportSource.vue';

export default defineComponent({
  name: 'BlockFiImport',
  components: { ImportSource }
});
</script>
