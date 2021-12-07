<template>
  <import-source source="bisq">
    <template #upload-title>
      <i18n tag="span" path="import_data.bisq.import">
        <strong>{{ $t('import_data.bisq.import_trade') }}</strong>
      </i18n>
    </template>
    <i18n tag="span" path="import_data.bisq.note">
      <strong>{{ $t('import_data.bisq.source_name') }}</strong>
    </i18n>
    <ul>
      <li>{{ $t('import_data.bisq.line_one') }}</li>
    </ul>
  </import-source>
</template>
<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import ImportSource from '@/components/import/ImportSource.vue';

export default defineComponent({
  name: 'BisqImport',
  components: { ImportSource }
});
</script>
